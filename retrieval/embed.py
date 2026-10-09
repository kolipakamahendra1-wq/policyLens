"""Text embeddings: Ollama nomic-embed-text, falling back to a deterministic
feature-hashing embedder (same dimension) when Ollama is unavailable."""
import hashlib
import logging
from functools import lru_cache

import httpx
import numpy as np

from backend.config import EMBED_DIM, EMBED_MODEL, OLLAMA_URL, USE_OLLAMA_EMBED
from backend.taxonomy import tokens

log = logging.getLogger(__name__)
HASH_MODEL = "hash-768"


def hash_embed(text: str) -> list[float]:
    vec = np.zeros(EMBED_DIM, dtype=np.float32)
    toks = tokens(text)
    for feat in toks + [a + "_" + b for a, b in zip(toks, toks[1:])]:
        h = int.from_bytes(hashlib.md5(feat.encode()).digest()[:8], "little")
        vec[h % EMBED_DIM] += 1.0 if (h >> 63) == 0 else -1.0
    n = np.linalg.norm(vec)
    return (vec / n if n else vec).tolist()


@lru_cache(maxsize=1)
def active_model() -> str:
    """Pick the embedder once per process so stored and query vectors match."""
    if USE_OLLAMA_EMBED:
        try:
            _ollama(["ping"])
            return EMBED_MODEL
        except Exception as e:  # noqa: BLE001 - any failure means fall back
            log.warning("Ollama embeddings unavailable (%s); using %s", e, HASH_MODEL)
    return HASH_MODEL


def _ollama(texts: list[str]) -> list[list[float]]:
    r = httpx.post(f"{OLLAMA_URL}/api/embed", json={"model": EMBED_MODEL, "input": texts}, timeout=60)
    r.raise_for_status()
    return r.json()["embeddings"]


def embed(texts: list[str], kind: str = "document") -> tuple[str, list[list[float]]]:
    """kind is "document" or "query" (nomic-embed-text expects task prefixes)."""
    model = active_model()
    if model == HASH_MODEL:
        return model, [hash_embed(t) for t in texts]
    return model, _ollama([f"search_{kind}: {t}" for t in texts])
