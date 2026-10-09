"""Deterministic guardrails applied after every evaluation, whatever produced it.

- Never claim compliance without evidence: PASS must cite real, relevant evidence.
- Policy text and interpretation are separate fields; the quote must be verbatim policy text.
- Uncertain decisions are UNKNOWN; uncertain high-risk decisions go to a human.
"""
import re

from agents.evaluator import Verdict

MIN_PASS_CONFIDENCE = 0.6
HIGH_RISK_PASS_CONFIDENCE = 0.85
# A requirement that sets a period or frequency can only pass if the evidence states one.
REQ_PERIOD = re.compile(r"\b(\d+\s*(days?|weeks?|months?|years?)|quarterly|annually|monthly|weekly|daily|retention period)\b", re.I)
EV_PERIOD = re.compile(r"(\d+\s*(d|days?|weeks?|months?|years?)\b|\b(quarterly|annually|monthly|weekly|daily|nightly)\b|"
                       r"(days?|months?|years?)\W*[:=]\s*\d+)", re.I)


def apply(requirement: dict, verdict: Verdict, evidence: list[dict]) -> tuple[Verdict, str, list[str]]:
    notes: list[str] = []
    v = verdict.model_copy()

    valid_ids = {e["id"] for e in evidence}
    cited = [i for i in v.evidence_ids if i in valid_ids]
    if len(cited) != len(v.evidence_ids):
        notes.append("Dropped citations to evidence that does not exist.")
    v.evidence_ids = cited

    if v.status == "PASS" and not cited:
        v.status = "UNKNOWN"
        notes.append("PASS without cited evidence downgraded to UNKNOWN.")
    if v.status == "PASS" and REQ_PERIOD.search(requirement["text"]):
        cited_text = "\n".join(e["text"] for e in evidence if e["id"] in cited)
        if not EV_PERIOD.search(cited_text):
            v.status = "UNKNOWN"
            notes.append("Requirement sets a period, but the cited evidence states none; PASS downgraded to UNKNOWN.")
    if v.status == "PASS" and v.confidence < MIN_PASS_CONFIDENCE:
        v.status = "UNKNOWN"
        notes.append(f"PASS with confidence {v.confidence:.2f} downgraded to UNKNOWN.")
    if requirement["risk"] == "high" and v.status == "PASS" and v.confidence < HIGH_RISK_PASS_CONFIDENCE:
        v.status = "NEEDS_HUMAN_REVIEW"
        notes.append("High-risk requirement: PASS below confidence threshold sent to human review.")
    if requirement["risk"] == "high" and v.status == "UNKNOWN" and cited:
        v.status = "NEEDS_HUMAN_REVIEW"
        notes.append("High-risk requirement with inconclusive evidence sent to human review.")

    quote = requirement["text"]
    if quote not in requirement["section_text"]:
        quote = requirement["section_text"]
        notes.append("Requirement text not found verbatim; quoting the full policy section.")
    return v, quote, notes


def overall(statuses: list[str]) -> str:
    return "Compliant" if statuses and all(s == "PASS" for s in statuses) else "Needs Review"
