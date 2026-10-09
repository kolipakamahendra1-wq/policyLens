"""Runtime settings, read from environment variables."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://policylens:policylens@localhost:5433/policylens")

# Free model only. Default: local Ollama via its OpenAI-compatible API.
# To use a free OpenRouter model instead: LLM_BASE_URL=https://openrouter.ai/api/v1,
# LLM_MODEL=<model>:free, LLM_API_KEY=<key>.
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:3b")
LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "120"))
USE_LLM = os.getenv("USE_LLM", "1") == "1"

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
USE_OLLAMA_EMBED = os.getenv("USE_OLLAMA_EMBED", "1") == "1"
EMBED_DIM = 768

JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-insecure-secret-change-me-in-production")
JWT_TTL_MINUTES = int(os.getenv("JWT_TTL_MINUTES", "480"))
# Fernet key for evidence at rest; dev default derived from JWT secret if unset.
EVIDENCE_KEY = os.getenv("EVIDENCE_KEY", "")
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", ROOT / "storage"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
