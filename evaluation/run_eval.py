"""Run the 50 synthetic cases through the review agent and report PRD §8 metrics.

    python -m evaluation.run_eval                 # offline: rules + hash embeddings (deterministic, CI)
    python -m evaluation.run_eval --live --limit 10   # free local LLM (Ollama qwen2.5:3b) + nomic embeddings

Uses its own database (policylens_eval by default) and re-ingests the sample policies each run.
"""
import argparse
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "data" / "eval_cases.json"
REPORTS = Path(__file__).resolve().parent / "reports"


def _setup_env(live: bool):
    os.environ["USE_LLM"] = "1" if live else "0"
    os.environ["USE_OLLAMA_EMBED"] = "1" if live else "0"
    os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://policylens:policylens@localhost:5433/policylens_eval")
    from sqlalchemy import create_engine, text

    base, name = os.environ["DATABASE_URL"].rsplit("/", 1)
    eng = create_engine(base + "/postgres", isolation_level="AUTOCOMMIT")
    with eng.connect() as c:
        if not c.scalar(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": name}):
            c.execute(text(f'CREATE DATABASE "{name}"'))
    eng.dispose()


def truth_for(req_types: list[str], variants: dict[str, str]) -> str:
    vs = [variants[t] for t in req_types if t in variants]
    if "bad" in vs:
        return "FAIL"
    if "good" in vs:
        return "PASS"
    return "UNKNOWN"


def reviewer_label(variants: dict[str, str]) -> str:
    vs = set(variants.values())
    return "reject" if "bad" in vs else "return" if "absent" in vs else "approve"


def system_recommendation(statuses: list[str]) -> str:
    if "FAIL" in statuses:
        return "reject"
    return "approve" if statuses and all(s == "PASS" for s in statuses) else "return"


def ratio(a: int, b: int) -> float | None:
    return round(a / b, 3) if b else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="use the free local LLM and Ollama embeddings")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    _setup_env(args.live)

    from backend.config import LLM_MODEL
    from backend.db import Requirement, SessionLocal, init_db
    from backend.taxonomy import EVIDENCE_LABELS
    from evidence.extract import evidence_types
    from agents.graph import run_review
    from policies.ingest import ingest_samples
    from retrieval.embed import active_model

    if not CASES.exists():
        from evaluation.generate_cases import OUT, generate

        OUT.write_text(json.dumps(generate(), indent=2))
    cases = json.loads(CASES.read_text())[: args.limit]

    init_db(drop=True)
    with SessionLocal() as s:
        ingest_samples(s)
        s.commit()
        all_reqs = list(s.query(Requirement))

    c = {k: 0 for k in ["targets", "matched", "strict", "lenient", "neg_truth", "false_pass", "cited", "grounded",
                        "absent", "requested", "agree", "llm", "rules"]}
    per_case = []
    t_start = time.time()
    for case in cases:
        variants = case["variants"]
        evidence = [{"id": e["id"], "filename": e["filename"], "text": e["text"],
                     "types": evidence_types(e["filename"], e["text"], e["type"])} for e in case["evidence"]]
        ev_type = {e["id"]: e["type"] for e in case["evidence"]}
        t0 = time.time()
        with SessionLocal() as s:
            state = run_review(s, case["description"], evidence)
        latency = time.time() - t0
        findings = {f["requirement"]["id"]: f for f in state["findings"]}

        targets = [r for r in all_reqs if set(r.evidence_types) & set(case["control_types"])]
        c["targets"] += len(targets)
        for r in targets:
            f = findings.get(r.id)
            if not f:
                continue
            c["matched"] += 1
            t = truth_for(r.evidence_types, variants)
            c["strict"] += f["status"] == t
            c["lenient"] += f["status"] == t or f["status"] == "NEEDS_HUMAN_REVIEW"

        # False compliance over every finding, not just targets.
        for f in state["findings"]:
            t = truth_for(f["requirement"]["evidence_types"], variants)
            if t != "PASS":
                c["neg_truth"] += 1
                c["false_pass"] += f["status"] == "PASS"
            if f["evidence_ids"]:
                c["cited"] += 1
                c["grounded"] += all(ev_type.get(i) in f["requirement"]["evidence_types"] for i in f["evidence_ids"])
            c["llm" if f["source"] != "rules" else "rules"] += 1

        for t, v in variants.items():
            if v == "absent":
                c["absent"] += 1
                c["requested"] += EVIDENCE_LABELS[t] in state["evidence_requested"]

        label = reviewer_label(variants)
        rec = system_recommendation([f["status"] for f in state["findings"]])
        c["agree"] += label == rec
        per_case.append({"id": case["id"], "reviewer": label, "system": rec, "result": state["result"],
                         "findings": len(state["findings"]), "latency_s": round(latency, 1)})

    metrics = {
        "policy_retrieval_recall": ratio(c["matched"], c["targets"]),
        "control_classification_accuracy_strict": ratio(c["strict"], c["matched"]),
        "control_classification_accuracy_with_human_review": ratio(c["lenient"], c["matched"]),
        "evidence_grounding": ratio(c["grounded"], c["cited"]),
        "false_compliance_rate": ratio(c["false_pass"], c["neg_truth"]),
        "missing_evidence_detection": ratio(c["requested"], c["absent"]),
        "human_reviewer_agreement": ratio(c["agree"], len(cases)),
    }
    report = {
        "mode": "live" if args.live else "offline",
        "llm": LLM_MODEL if args.live else "disabled (rule-based fallback)",
        "embeddings": active_model(),
        "cases": len(cases),
        "metrics": metrics,
        "counts": c,
        "avg_latency_s": round(sum(p["latency_s"] for p in per_case) / max(len(per_case), 1), 1),
        "total_s": round(time.time() - t_start, 1),
        "per_case": per_case,
    }
    REPORTS.mkdir(exist_ok=True)
    out = REPORTS / f"eval-{report['mode']}.json"
    out.write_text(json.dumps(report, indent=2))

    print(f"PolicyLens evaluation ({report['mode']}, {len(cases)} cases, llm={report['llm']}, embeddings={report['embeddings']})")
    for k, v in metrics.items():
        print(f"  {k:<52} {v}")
    print(f"  {'avg latency per case (s)':<52} {report['avg_latency_s']}")
    print(f"  decided by llm / rules: {c['llm']} / {c['rules']}")
    print(f"Report: {out}")
    return report


if __name__ == "__main__":
    main()
