from agents import guardrails
from agents.evaluator import Verdict, evaluate_requirement, rule_verdict
from agents.graph import run_review

REQ = {
    "id": 1, "code": "X-1.1", "text": "Data must be encrypted at rest.", "risk": "medium",
    "evidence_types": ["encryption"], "citation": "X §1", "section_text": "Data must be encrypted at rest.",
}
EV = {"id": 7, "filename": "kms.yaml", "types": ["encryption"], "text": "storage_encrypted: true\nkms_key: alias/db"}


def test_no_evidence_is_unknown_never_pass():
    v = evaluate_requirement(REQ, [], "new db")
    assert v.status == "UNKNOWN" and v.evidence_ids == []


def test_rules_pass_fail_and_contradiction():
    assert rule_verdict(REQ, [EV]).status == "PASS"
    bad = {**EV, "id": 8, "text": "storage_encrypted: false"}
    assert rule_verdict(REQ, [bad]).status == "FAIL"
    assert rule_verdict(REQ, [EV, bad]).status == "NEEDS_HUMAN_REVIEW"


def test_guardrail_pass_without_evidence_becomes_unknown():
    v, _, notes = guardrails.apply(REQ, Verdict(status="PASS", interpretation="ok", confidence=0.95), [EV])
    assert v.status == "UNKNOWN" and notes


def test_guardrail_drops_hallucinated_citations():
    v, _, _ = guardrails.apply(REQ, Verdict(status="PASS", evidence_ids=[999], interpretation="ok", confidence=0.95), [EV])
    assert v.status == "UNKNOWN" and v.evidence_ids == []


def test_guardrail_high_risk_low_confidence_goes_to_human():
    high = {**REQ, "risk": "high"}
    v, _, _ = guardrails.apply(high, Verdict(status="PASS", evidence_ids=[7], interpretation="ok", confidence=0.7), [EV])
    assert v.status == "NEEDS_HUMAN_REVIEW"
    v, _, _ = guardrails.apply(high, Verdict(status="PASS", evidence_ids=[7], interpretation="ok", confidence=0.95), [EV])
    assert v.status == "PASS"


def test_guardrail_quote_must_be_verbatim():
    req = {**REQ, "text": "Invented text."}
    _, quote, notes = guardrails.apply(req, Verdict(status="UNKNOWN", interpretation="x", confidence=0), [])
    assert quote == REQ["section_text"] and notes


def test_confidence_percent_normalised_and_status_uppercased():
    v = Verdict(status="needs human review", interpretation="x", confidence=85)
    assert v.status == "NEEDS_HUMAN_REVIEW" and v.confidence == 0.85


def test_prd_example_needs_review_with_gaps(session):
    evidence = [
        {"id": 1, "filename": "encryption.yaml", "types": ["encryption"],
         "text": "database: encrypted at rest with AES-256, kms key alias/customers\ntls: 1.2 minimum"},
        {"id": 2, "filename": "logging.yaml", "types": ["logging"],
         "text": "audit logging: enabled for all record access\nlog retention: 400 days in central SIEM"},
    ]
    state = run_review(session, "We are deploying a new API that stores customer information.", evidence)
    assert state["result"] == "Needs Review"
    by_type = {}
    for f in state["findings"]:
        for t in f["requirement"]["evidence_types"]:
            by_type.setdefault(t, set()).add(f["status"])
    assert by_type["retention"] == {"UNKNOWN"}
    assert by_type["iam"] == {"UNKNOWN"}
    assert "PASS" in by_type["logging"]
    assert "retention configuration" in state["evidence_requested"]
    assert "IAM configuration" in state["evidence_requested"]
    for f in state["findings"]:
        assert f["policy_quote"] in f["requirement"]["section_text"]
        assert f["status"] != "PASS" or f["evidence_ids"]


def test_classify_word_boundaries_and_log_retention():
    from backend.taxonomy import classify

    assert classify("log retention: 400 days, audit logging enabled") == ["logging"]
    assert classify("settle the bill") == []
    assert classify("retention_days: 30") == ["retention"]


def test_guardrail_pass_needs_period_in_evidence_when_requirement_has_one():
    req = {**REQ, "evidence_types": ["logging"], "text": "Audit logs must be retained for at least 1 year.",
           "section_text": "Audit logs must be retained for at least 1 year."}
    no_period = {"id": 3, "filename": "log.yaml", "types": ["logging"], "text": "audit_logging: enabled\nsink: siem"}
    v, _, notes = guardrails.apply(req, Verdict(status="PASS", evidence_ids=[3], interpretation="ok", confidence=0.95), [no_period])
    assert v.status == "UNKNOWN" and any("period" in n for n in notes)
    with_period = {**no_period, "text": "audit_logging: enabled\nlog_retention_days: 400"}
    v, _, _ = guardrails.apply(req, Verdict(status="PASS", evidence_ids=[3], interpretation="ok", confidence=0.95), [with_period])
    assert v.status == "PASS"


def test_rules_treat_not_completed_as_negative():
    req = {**REQ, "evidence_types": ["privacy"]}
    ev = {"id": 9, "filename": "dpia.md", "types": ["privacy"], "text": "Privacy impact assessment (DPIA): not completed."}
    assert rule_verdict(req, [ev]).status == "FAIL"
