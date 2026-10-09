import os
import shutil

# Tests are deterministic: no LLM, hash embeddings. Run against a separate database.
os.environ.setdefault("USE_LLM", "0")
os.environ.setdefault("USE_OLLAMA_EMBED", "0")
os.environ.setdefault("STORAGE_DIR", os.path.join(os.path.dirname(__file__), "..", "storage", "test"))
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://policylens:policylens@localhost:5433/policylens_test"
)

import pytest  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402


def _ensure_test_db():
    url = os.environ["DATABASE_URL"]
    base, name = url.rsplit("/", 1)
    eng = create_engine(base + "/postgres", isolation_level="AUTOCOMMIT")
    with eng.connect() as c:
        if not c.scalar(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": name}):
            c.execute(text(f'CREATE DATABASE "{name}"'))
    eng.dispose()


_ensure_test_db()
shutil.rmtree(os.environ["STORAGE_DIR"], ignore_errors=True)

from backend.db import SessionLocal, init_db  # noqa: E402
from policies.ingest import ingest_samples  # noqa: E402


@pytest.fixture(scope="session")
def seeded():
    init_db(drop=True)
    with SessionLocal() as s:
        ingest_samples(s)
        s.commit()
    return True


@pytest.fixture
def session(seeded):
    with SessionLocal() as s:
        yield s
        s.rollback()
