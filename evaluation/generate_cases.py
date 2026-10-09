"""Generate 50 synthetic policy-review cases with ground truth.

Each case combines 1-3 change topics. Every control area a topic touches gets
evidence that either meets the policy ("good"), visibly violates it ("bad"), or is
missing ("absent"). Ground truth per requirement is derived in run_eval from these
variants: bad -> FAIL, good -> PASS, absent -> UNKNOWN.

    python -m evaluation.generate_cases   # writes data/eval_cases.json
"""
import json
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "eval_cases.json"
SEED = 7
N_CASES = 50

TOPICS = {
    "stores customer information in a new Postgres database": ["data_classification", "retention", "iam", "encryption"],
    "exposes a public REST API to partners": ["api_spec"],
    "adds an admin console for support staff": ["iam"],
    "records audit logs of every customer record access": ["logging"],
    "processes personal data such as email addresses and phone numbers": ["privacy"],
    "ships through a new production deployment pipeline": ["deployment", "change_management"],
}
SUBJECTS = ["a billing service", "the customer profile API", "a loyalty-points service", "an internal reporting tool",
            "a mobile backend", "a partner integration", "the search indexer", "a notifications service"]

EVIDENCE = {
    "encryption": {
        "file": "encryption.yaml",
        "good": "storage_encrypted: true\nencryption_at_rest: AES-256 with kms_key alias/app\ntls_min_version: 1.2\n"
                "secrets: stored in secrets manager (vault), none in source control",
        "bad": "storage_encrypted: false\ntls_min_version: 1.0\nsecrets: committed in the config repo",
    },
    "retention": {
        "file": "retention.yaml",
        "good": "retention:\n  customer_records_days: 365\n  lifecycle_rule: automated purge job, nightly\n"
                "  backups_follow_primary_retention: true",
        "bad": "retention: none\nlifecycle_rule: disabled\nbackups_follow_primary_retention: false",
    },
    "iam": {
        "file": "iam-policy.json",
        "good": '{"role": "app-prod", "least_privilege": true, "mfa_required_for_admin": true, '
                '"access_review": "quarterly by data owner"}',
        "bad": '{"role": "shared-admin", "least_privilege": false, "mfa_required_for_admin": false, "access_review": "none"}',
    },
    "logging": {
        "file": "logging.yaml",
        "good": "audit_logging: enabled\nfields: actor, record_id, timestamp\nlog_retention_days: 400 in central SIEM\n"
                "redaction: passwords and tokens masked",
        "bad": "audit_logging: disabled\nlog_retention_days: 0\nredaction: disabled, tokens logged in plaintext",
    },
    "data_classification": {
        "file": "classification.md",
        "good": "Data classification: Confidential. Data owner: J. Rivera. Restricted data is never copied to "
                "non-production; fixtures are synthetic.",
        "bad": "Data classification: TBD. Data owner: missing. Production snapshots are copied to staging.",
    },
    "deployment": {
        "file": "deploy-plan.md",
        "good": "Deploy via the approved CI/CD pipeline with automated tests. Rollback: documented blue/green switch. "
                "Release: canary at 5%. Breaking API changes ship as /v2.",
        "bad": "Deploy: manual from a laptop, no pipeline. Rollback: none. Release: all at once.",
    },
    "api_spec": {
        "file": "openapi.yaml",
        "good": "openapi: 3.1.0\nauthentication scheme: OAuth2 client credentials\nrate limit: 100 requests/minute\n"
                "api versioning: path prefix /v1, breaking changes go to /v2",
        "bad": "openapi: missing\nauthentication: none\nrate limit: disabled",
    },
    "change_management": {
        "file": "change-ticket.txt",
        "good": "Change ticket CHG-1234 links to this review. Change approval: approved by a reviewer who is not the author.",
        "bad": "Change ticket: none. Change approval: missing.",
    },
    "privacy": {
        "file": "dpia.md",
        "good": "Privacy impact assessment (DPIA) completed 2026-09-01. Personal data limited to email; "
                "data minimisation reviewed.",
        "bad": "Privacy impact assessment (DPIA): not completed. Personal data: collecting full contact history.",
    },
}


def generate(seed: int = SEED, n: int = N_CASES) -> list[dict]:
    rng = random.Random(seed)
    cases = []
    for i in range(n):
        topics = rng.sample(list(TOPICS), rng.choice([1, 2, 2, 3]))
        subject = rng.choice(SUBJECTS)
        description = f"We are launching {subject} that " + "; it also ".join(topics) + "."
        types = sorted({t for topic in topics for t in TOPICS[topic]})
        variants, evidence = {}, []
        for t in types:
            v = rng.choices(["good", "bad", "absent"], weights=[0.5, 0.2, 0.3])[0]
            variants[t] = v
            if v != "absent":
                evidence.append({"id": len(evidence) + 1, "type": t, "filename": EVIDENCE[t]["file"],
                                 "text": EVIDENCE[t][v]})
        cases.append({"id": i + 1, "description": description, "control_types": types,
                      "variants": variants, "evidence": evidence})
    return cases


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(generate(), indent=2))
    print(f"Wrote {N_CASES} cases to {OUT}")
