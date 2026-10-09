"""Store a parsed policy with embedded sections. Re-uploading a policy key replaces it."""
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db import Policy, Requirement, Section, audit
from policies.parser import parse_policy
from retrieval.embed import embed

SAMPLE_DIR = Path(__file__).parent / "sample"


def ingest(session: Session, data: bytes, filename: str, actor: str = "system") -> Policy:
    parsed = parse_policy(data, filename)
    if not parsed.sections:
        raise ValueError("No sections found in policy document")
    existing = session.scalar(select(Policy).where(Policy.policy_key == parsed.key))
    if existing:
        session.delete(existing)
        session.flush()

    policy = Policy(policy_key=parsed.key, title=parsed.title, domain=parsed.domain, filename=filename)
    model, vectors = embed([f"{parsed.title}. {s.heading}. {s.text}" for s in parsed.sections])
    for s, vec in zip(parsed.sections, vectors):
        section = Section(
            citation=f"{parsed.key} §{s.number}",
            heading=s.heading,
            text=s.text,
            embedding=vec,
            embed_model=model,
        )
        section.requirements = [
            Requirement(code=r.code, text=r.text, risk=r.risk, evidence_types=r.evidence_types) for r in s.requirements
        ]
        policy.sections.append(section)
    session.add(policy)
    session.flush()
    audit(session, actor, "policy.ingest", f"policy:{policy.id}", key=parsed.key, sections=len(parsed.sections))
    return policy


def ingest_samples(session: Session) -> list[Policy]:
    return [ingest(session, p.read_bytes(), p.name) for p in sorted(SAMPLE_DIR.glob("*.md"))]
