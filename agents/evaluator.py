"""Evaluate one requirement against the evidence.

Requirements with no evidence of a matching type are UNKNOWN without calling the
model (compliance can never be claimed without evidence). Otherwise the LLM decides;
if it is disabled or fails, a rule-based check runs instead.
"""
import logging
import re
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

from agents import llm
from backend.config import LLM_MODEL, USE_LLM
from backend.taxonomy import EVIDENCE_KEYWORDS

log = logging.getLogger(__name__)
Status = Literal["PASS", "FAIL", "UNKNOWN", "NEEDS_HUMAN_REVIEW"]

NEGATIVE = re.compile(
    r"(:\s*(false|no|none|off|disabled|null|0)\b|=\s*(false|no|none|off|0)\b|"
    r"\b(not (enabled|configured|encrypted|defined|set|completed|approved|reviewed)|disabled|no retention|unencrypted|plaintext|"
    r"without (mfa|encryption|retention)|missing|todo|tbd)\b)",
    re.I,
)

SYSTEM = """You are a compliance evaluator. Decide whether the EVIDENCE shows that the POLICY REQUIREMENT is met.
Rules:
- PASS only if the evidence explicitly shows the requirement is met. Cite the evidence ids you relied on.
- FAIL if the evidence explicitly shows it is not met.
- UNKNOWN if the evidence does not say enough to decide.
- NEEDS_HUMAN_REVIEW if the evidence is contradictory or the decision needs judgement.
- Never assume facts that are not in the evidence.
Reply with JSON only: {"status": "...", "evidence_ids": [int], "interpretation": "one or two sentences", "confidence": 0.0-1.0}"""


class Verdict(BaseModel):
    status: Status
    evidence_ids: list[int] = Field(default_factory=list)
    interpretation: str
    confidence: float = Field(ge=0, le=1)
    source: str = "rules"

    @field_validator("status", mode="before")
    @classmethod
    def _upper(cls, v):
        return str(v).strip().upper().replace(" ", "_")

    @field_validator("confidence", mode="before")
    @classmethod
    def _fraction(cls, v):
        v = float(v)
        return v / 100 if v > 1 else v  # small models sometimes answer in percent


def relevant_evidence(requirement: dict, evidence: list[dict]) -> list[dict]:
    want = set(requirement["evidence_types"])
    return [e for e in evidence if want & set(e["types"])]


def _relevant_lines(requirement: dict, text: str) -> list[str]:
    kws = [k for t in requirement["evidence_types"] for k in EVIDENCE_KEYWORDS.get(t, [])]
    return [ln for ln in text.splitlines() if any(k in ln.lower() for k in kws)]


def rule_verdict(requirement: dict, evidence: list[dict]) -> Verdict:
    pos, neg = [], []
    for e in evidence:
        lines = _relevant_lines(requirement, e["text"]) or ([e["text"]] if e["text"] else [])
        if any(NEGATIVE.search(ln) for ln in lines):
            neg.append(e["id"])
        elif lines:
            pos.append(e["id"])
    if neg and pos:
        return Verdict(status="NEEDS_HUMAN_REVIEW", evidence_ids=pos + neg, confidence=0.5,
                       interpretation="Evidence is contradictory: some items support the requirement and some contradict it.")
    if neg:
        return Verdict(status="FAIL", evidence_ids=neg, confidence=0.7,
                       interpretation="Evidence indicates the control is disabled, missing or not configured.")
    if pos:
        return Verdict(status="PASS", evidence_ids=pos, confidence=0.75,
                       interpretation="Evidence of the required control type is present; specific values were matched by keyword only.")
    return Verdict(status="UNKNOWN", confidence=0.0,
                   interpretation="Attached evidence does not describe this control.")


def llm_verdict(requirement: dict, evidence: list[dict], description: str) -> Verdict:
    ev = "\n\n".join(f"[evidence id={e['id']}] {e['filename']}\n{e['text'][:1500]}" for e in evidence)
    user = (
        f"POLICY REQUIREMENT ({requirement['citation']}): {requirement['text']}\n\n"
        f"CHANGE REQUEST: {description[:1500]}\n\nEVIDENCE:\n{ev}"
    )
    data = llm.chat_json(SYSTEM, user)
    return Verdict(**{**data, "source": LLM_MODEL})


def evaluate_requirement(requirement: dict, evidence: list[dict], description: str) -> Verdict:
    candidates = relevant_evidence(requirement, evidence)
    if not candidates:
        return Verdict(status="UNKNOWN", confidence=0.0,
                       interpretation="No evidence of the required type was attached.")
    if USE_LLM:
        try:
            return llm_verdict(requirement, candidates, description)
        except (ValidationError, ValueError, KeyError, TypeError) as e:
            log.warning("LLM returned an invalid verdict (%s); using rules", e)
        except Exception as e:  # noqa: BLE001 - network/model errors fall back to rules
            log.warning("LLM unavailable (%s); using rules", e)
    return rule_verdict(requirement, candidates)
