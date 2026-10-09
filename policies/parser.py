"""Parse policy documents (Markdown, HTML, DOCX, PDF) into sections and requirements.

Every format is first normalised to Markdown-style text, then one parser splits it
into `## ` sections. Sentences containing must/shall/required become requirements.
A requirement may carry an explicit tag `(risk: high; evidence: iam, logging)`;
otherwise risk and evidence types are inferred from keywords.
"""
import io
import re
from dataclasses import dataclass, field
from pathlib import Path

from backend.taxonomy import classify

REQ_WORDS = re.compile(r"\b(must|shall|required|is prohibited)\b", re.I)
TAG = re.compile(r"\(risk:\s*(high|medium|low)\s*(?:;\s*evidence:\s*([a-z_,\s]+))?\)", re.I)
NUMBER = re.compile(r"^(\d+(?:\.\d+)*)\.?\s+(.*)$")
HIGH_RISK_WORDS = ["customer", "personal data", "pii", "encrypt", "production", "secret", "credential", "privileged"]


@dataclass
class ParsedRequirement:
    code: str
    text: str
    risk: str
    evidence_types: list[str]


@dataclass
class ParsedSection:
    number: str
    heading: str
    text: str
    requirements: list[ParsedRequirement] = field(default_factory=list)


@dataclass
class ParsedPolicy:
    key: str
    title: str
    domain: str
    sections: list[ParsedSection]


def to_markdown(data: bytes, filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in (".md", ".markdown", ".txt"):
        return data.decode("utf-8", errors="replace")
    if ext in (".html", ".htm"):
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(data, "html.parser")
        lines = []
        for el in soup.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
            t = el.get_text(" ", strip=True)
            if el.name[0] == "h":
                lines.append("#" * int(el.name[1]) + " " + t)
            elif el.name == "li":
                lines.append("- " + t)
            else:
                lines.append(t)
        return "\n".join(lines)
    if ext == ".docx":
        import docx

        lines = []
        for p in docx.Document(io.BytesIO(data)).paragraphs:
            style = p.style.name if p.style is not None else ""
            m = re.match(r"Heading (\d)", style)
            if m:
                lines.append("#" * int(m.group(1)) + " " + p.text)
            elif style == "Title":
                lines.append("# " + p.text)
            else:
                lines.append(p.text)
        return "\n".join(lines)
    if ext == ".pdf":
        from pypdf import PdfReader

        text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages)
        lines = []
        for line in text.splitlines():
            s = line.strip()
            # Numbered short lines such as "2.1 Least privilege" are treated as headings.
            if NUMBER.match(s) and len(s) < 80 and not REQ_WORDS.search(s):
                lines.append("## " + s)
            else:
                lines.append(s)
        return "\n".join(lines)
    raise ValueError(f"Unsupported policy format: {ext}")


def _sentences(body: str) -> list[str]:
    out = []
    for line in body.splitlines():
        line = line.strip().lstrip("-*").strip()
        if not line:
            continue
        # Keep a trailing tag attached to its sentence.
        out.extend(s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z])", line) if s.strip())
    return out


def _requirement(sentence: str, code: str) -> ParsedRequirement | None:
    if not REQ_WORDS.search(sentence):
        return None
    tag = TAG.search(sentence)
    clean = TAG.sub("", sentence).strip()
    if tag:
        risk = tag.group(1).lower()
        ev = [e.strip() for e in (tag.group(2) or "").split(",") if e.strip()] or classify(clean)
    else:
        low = clean.lower()
        risk = "high" if any(w in low for w in HIGH_RISK_WORDS) else "medium"
        ev = classify(clean)
    return ParsedRequirement(code=code, text=clean, risk=risk, evidence_types=ev)


def parse_markdown(md: str, filename: str) -> ParsedPolicy:
    title, key, domain = "", "", ""
    sections: list[ParsedSection] = []
    current: ParsedSection | None = None
    body: list[str] = []

    def flush():
        if current is not None:
            current.text = "\n".join(body).strip()

    for raw in md.splitlines():
        line = raw.rstrip()
        if line.startswith("# ") and not title:
            title = line[2:].strip()
            continue
        m = re.match(r"^(?:\*\*)?(policy id|domain)(?:\*\*)?\s*:\s*(.+)$", line.strip(), re.I)
        if m and current is None:
            if m.group(1).lower() == "policy id":
                key = m.group(2).strip().strip("*")
            else:
                domain = m.group(2).strip().strip("*")
            continue
        if re.match(r"^#{2,4}\s", line):
            flush()
            heading = line.lstrip("#").strip()
            nm = NUMBER.match(heading)
            number = nm.group(1) if nm else str(len(sections) + 1)
            heading = nm.group(2) if nm else heading
            current = ParsedSection(number=number, heading=heading, text="")
            sections.append(current)
            body = []
            continue
        if current is not None:
            body.append(line)
    flush()

    stem = Path(filename).stem
    key = key or re.sub(r"[^A-Z0-9]+", "-", stem.upper()).strip("-")
    title = title or stem.replace("_", " ").replace("-", " ").title()
    domain = domain or (classify(title + " " + md[:2000]) or ["general"])[0]

    for s in sections:
        i = 0
        for sent in _sentences(s.text):
            req = _requirement(sent, f"{key}-{s.number}.{i + 1}")
            if req:
                s.requirements.append(req)
                i += 1
        s.text = TAG.sub("", s.text).replace("  ", " ").strip()
    sections = [s for s in sections if s.text]
    return ParsedPolicy(key=key, title=title, domain=domain, sections=sections)


def parse_policy(data: bytes, filename: str) -> ParsedPolicy:
    return parse_markdown(to_markdown(data, filename), filename)
