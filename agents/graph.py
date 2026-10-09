"""The review agent as a LangGraph pipeline:

    extract_claims -> match -> evaluate -> guardrails -> summarize

The agent only reads policies and evidence and returns findings. It has no tools
that write anywhere else, so it cannot modify production systems.
"""
from typing import TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from agents import guardrails
from agents.evaluator import evaluate_requirement, relevant_evidence
from backend.taxonomy import EVIDENCE_LABELS
from evidence.extract import extract_claims
from retrieval.hybrid import search

MATCH_K = 10


class ReviewState(TypedDict, total=False):
    description: str
    evidence: list[dict]  # {id, filename, types, text}
    claims: list[dict]
    requirements: list[dict]
    raw_verdicts: list[dict]
    findings: list[dict]
    result: str
    evidence_requested: list[str]
    summary: str


def match_requirements(session: Session, description: str, claims: list[dict], evidence: list[dict] = ()) -> list[dict]:
    """Retrieve applicable policy sections and flatten them into requirements with citations."""
    hits = search(session, description, k=MATCH_K)
    # Control areas named in the request or covered by attached evidence are always checked.
    claimed = {t for c in claims for t in c["types"]} | {t for e in evidence for t in e["types"]}
    if claimed:
        seen = {h.section.id for h in hits}
        hits += [h for h in search(session, description, k=50) if h.section.id not in seen
                 and claimed & {t for r in h.section.requirements for t in r.evidence_types}]
    reqs = []
    for h in hits:
        s = h.section
        for r in s.requirements:
            reqs.append({
                "id": r.id, "code": r.code, "text": r.text, "risk": r.risk,
                "evidence_types": r.evidence_types, "citation": s.citation,
                "heading": s.heading, "section_text": s.text, "policy_title": s.policy.title,
                "retrieval_score": round(h.score, 4),
            })
    return reqs


def build_graph(session: Session):
    def claims_node(state: ReviewState):
        return {"claims": extract_claims(state["description"])}

    def match_node(state: ReviewState):
        return {"requirements": match_requirements(session, state["description"], state["claims"], state["evidence"])}

    def evaluate_node(state: ReviewState):
        out = []
        for r in state["requirements"]:
            v = evaluate_requirement(r, state["evidence"], state["description"])
            out.append({"requirement": r, "verdict": v})
        return {"raw_verdicts": out}

    def guardrails_node(state: ReviewState):
        findings = []
        for item in state["raw_verdicts"]:
            r = item["requirement"]
            v, quote, notes = guardrails.apply(r, item["verdict"], relevant_evidence(r, state["evidence"]))
            findings.append({
                "requirement": r, "status": v.status, "evidence_ids": v.evidence_ids,
                "policy_quote": quote, "interpretation": v.interpretation,
                "confidence": v.confidence, "source": v.source, "notes": notes,
            })
        return {"findings": findings}

    def summarize_node(state: ReviewState):
        f = state["findings"]
        result = guardrails.overall([x["status"] for x in f])
        missing = []
        for x in f:
            if x["status"] != "PASS" and not x["evidence_ids"]:
                for t in x["requirement"]["evidence_types"]:
                    label = EVIDENCE_LABELS.get(t, t)
                    if label not in missing:
                        missing.append(label)
        counts = {s: sum(1 for x in f if x["status"] == s) for s in ("PASS", "FAIL", "UNKNOWN", "NEEDS_HUMAN_REVIEW")}
        policies = sorted({x["requirement"]["policy_title"] for x in f})
        summary = (
            f"{len(f)} requirements from {len(policies)} policies were checked: "
            f"{counts['PASS']} pass, {counts['FAIL']} fail, {counts['UNKNOWN']} unknown, "
            f"{counts['NEEDS_HUMAN_REVIEW']} need human review. Result: {result}."
        )
        if missing:
            summary += " Evidence requested: " + ", ".join(missing) + "."
        return {"result": result, "evidence_requested": missing, "summary": summary}

    g = StateGraph(ReviewState)
    for name, fn in [("extract_claims", claims_node), ("match", match_node), ("evaluate", evaluate_node),
                     ("guardrails", guardrails_node), ("summarize", summarize_node)]:
        g.add_node(name, fn)
    g.set_entry_point("extract_claims")
    g.add_edge("extract_claims", "match")
    g.add_edge("match", "evaluate")
    g.add_edge("evaluate", "guardrails")
    g.add_edge("guardrails", "summarize")
    g.add_edge("summarize", END)
    return g.compile()


def run_review(session: Session, description: str, evidence: list[dict]) -> ReviewState:
    return build_graph(session).invoke({"description": description, "evidence": evidence})
