"""Turn uploaded evidence into searchable text, and pull claims out of a change request."""
import io
import re
from pathlib import Path

from backend.taxonomy import classify

TEXT_EXTS = {".txt", ".md", ".json", ".yaml", ".yml", ".tf", ".hcl", ".toml", ".ini", ".conf", ".cfg", ".xml", ".csv"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
MAX_TEXT = 20_000


def extract_text(data: bytes, filename: str, note: str = "") -> str:
    """Images are kept as references only; the uploader's note describes them."""
    ext = Path(filename).suffix.lower()
    text = ""
    if ext in TEXT_EXTS:
        text = data.decode("utf-8", errors="replace")
    elif ext in (".html", ".htm"):
        from bs4 import BeautifulSoup

        text = BeautifulSoup(data, "html.parser").get_text("\n", strip=True)
    elif ext == ".pdf":
        from pypdf import PdfReader

        text = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(data)).pages)
    elif ext == ".docx":
        import docx

        text = "\n".join(p.text for p in docx.Document(io.BytesIO(data)).paragraphs)
    elif ext not in IMAGE_EXTS:
        text = data.decode("utf-8", errors="replace")
    if note:
        text = f"{note}\n{text}"
    return text[:MAX_TEXT].strip()


def evidence_types(filename: str, text: str, declared: str | None = None) -> list[str]:
    types = classify(filename.replace("_", " ").replace("-", " ") + "\n" + text)
    if declared and declared not in types:
        types.insert(0, declared)
    return types


def extract_claims(description: str) -> list[dict]:
    """Sentences of the change request that touch a control area."""
    claims = []
    for sent in re.split(r"(?<=[.!?])\s+|\n+", description):
        sent = sent.strip()
        if sent:
            types = classify(sent)
            if types or re.search(r"\b(customer|personal|store|deploy|api)\b", sent, re.I):
                claims.append({"text": sent, "types": types})
    return claims
