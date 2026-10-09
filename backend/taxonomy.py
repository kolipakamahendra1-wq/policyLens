"""Shared vocabulary of control/evidence types, used by the policy parser,
evidence extraction and the rule-based evaluator."""
import re

EVIDENCE_KEYWORDS: dict[str, list[str]] = {
    "data_classification": ["classif", "sensitivity label", "data owner"],
    "retention": ["retention", "retain", "purge", "ttl", "lifecycle"],
    "iam": ["iam", "least privilege", "role-based", "rbac", "permission", "mfa", "access review", "access control", "admin"],
    "encryption": ["encrypt", "tls", "kms", "at rest", "in transit", "aes"],
    "logging": ["audit log", "access log", "logging", "log retention", "siem", "cloudtrail", "audit trail"],
    "deployment": ["deploy", "rollback", "canary", "pipeline", "release"],
    "api_spec": ["openapi", "rate limit", "api versioning", "breaking change", "authentication scheme", "api spec"],
    "change_management": ["change ticket", "change request", "cab", "change approval"],
    "privacy": ["personal data", "pii", "consent", "privacy impact", "dpia", "data subject"],
}

EVIDENCE_LABELS = {
    "data_classification": "data classification record",
    "retention": "retention configuration",
    "iam": "IAM configuration",
    "encryption": "encryption configuration",
    "logging": "logging configuration",
    "deployment": "deployment / rollback plan",
    "api_spec": "API specification",
    "change_management": "change ticket / approval record",
    "privacy": "privacy impact assessment",
}


# Phrases that contain another type's keyword but do not belong to it.
EXCLUDE = {"retention": ["log retention"]}
_PATTERNS = {t: re.compile("|".join(r"\b" + re.escape(k) for k in kws)) for t, kws in EVIDENCE_KEYWORDS.items()}


def classify(text: str) -> list[str]:
    """Return evidence types whose keywords appear (at a word start) in the text."""
    low = text.lower()
    out = []
    for t, pat in _PATTERNS.items():
        scoped = low
        for phrase in EXCLUDE.get(t, []):
            scoped = scoped.replace(phrase, " ")
        if pat.search(scoped):
            out.append(t)
    return out


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())
