"""Evidence files are encrypted at rest (Fernet) and addressed by SHA-256."""
import base64
import hashlib

from cryptography.fernet import Fernet

from backend.config import EVIDENCE_KEY, JWT_SECRET, STORAGE_DIR


def _fernet() -> Fernet:
    key = EVIDENCE_KEY or base64.urlsafe_b64encode(hashlib.sha256(JWT_SECRET.encode()).digest()).decode()
    return Fernet(key)


def save(data: bytes) -> tuple[str, str]:
    """Encrypt and store; returns (sha256, path)."""
    digest = hashlib.sha256(data).hexdigest()
    folder = STORAGE_DIR / "evidence"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{digest}.bin"
    if not path.exists():
        path.write_bytes(_fernet().encrypt(data))
    return digest, str(path)


def load(path: str) -> bytes:
    with open(path, "rb") as f:
        return _fernet().decrypt(f.read())
