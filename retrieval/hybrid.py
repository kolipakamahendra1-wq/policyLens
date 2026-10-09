"""Hybrid policy retrieval: BM25 + pgvector, fused with reciprocal rank fusion,
then reranked by query/section term coverage and control-type overlap."""
import logging
from dataclasses import dataclass

from rank_bm25 import BM25Okapi
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.db import Section
from backend.taxonomy import classify, tokens
from retrieval.embed import embed

log = logging.getLogger(__name__)
RRF_K = 60
CANDIDATES = 30


@dataclass
class Hit:
    section: Section
    score: float
    bm25_rank: int | None
    vector_rank: int | None


def _doc(s: Section) -> str:
    return f"{s.policy.title} {s.heading} {s.text}"


def search(session: Session, query: str, k: int = 8, only_with_requirements: bool = True) -> list[Hit]:
    stmt = select(Section).options(selectinload(Section.policy), selectinload(Section.requirements))
    sections = list(session.scalars(stmt))
    if only_with_requirements:
        sections = [s for s in sections if s.requirements]
    if not sections:
        return []
    by_id = {s.id: s for s in sections}

    # Keyword leg.
    bm25 = BM25Okapi([tokens(_doc(s)) for s in sections])
    scores = bm25.get_scores(tokens(query))
    bm25_order = [sections[i].id for i in sorted(range(len(sections)), key=lambda i: -scores[i]) if scores[i] > 0]
    bm25_order = bm25_order[:CANDIDATES]

    # Vector leg (only sections embedded with the same model as the query).
    # If the embedding service fails, keyword retrieval alone still answers.
    try:
        model, (qvec,) = embed([query], kind="query")
        vec_stmt = (
            select(Section.id)
            .where(Section.embed_model == model, Section.id.in_(list(by_id)))
            .order_by(Section.embedding.cosine_distance(qvec))
            .limit(CANDIDATES)
        )
        vec_order = list(session.scalars(vec_stmt))
    except Exception as e:  # noqa: BLE001
        log.warning("Query embedding failed (%s); using keyword retrieval only", e)
        vec_order = []

    # Reciprocal rank fusion.
    fused: dict[int, float] = {}
    for order in (bm25_order, vec_order):
        for rank, sid in enumerate(order):
            fused[sid] = fused.get(sid, 0.0) + 1.0 / (RRF_K + rank + 1)

    # Rerank: reward query-term coverage of the section and shared control types.
    q_terms = set(tokens(query))
    q_types = set(classify(query))
    hits = []
    for sid, base in fused.items():
        s = by_id[sid]
        s_terms = set(tokens(_doc(s)))
        coverage = len(q_terms & s_terms) / max(len(q_terms), 1)
        s_types = {t for r in s.requirements for t in r.evidence_types}
        overlap = len(q_types & s_types)
        score = base + 0.01 * coverage + 0.01 * overlap
        hits.append(
            Hit(
                section=s,
                score=score,
                bm25_rank=bm25_order.index(sid) + 1 if sid in bm25_order else None,
                vector_rank=vec_order.index(sid) + 1 if sid in vec_order else None,
            )
        )
    hits.sort(key=lambda h: -h.score)
    return hits[:k]
