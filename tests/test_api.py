import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture(scope="module")
def client(seeded):
    with TestClient(app) as c:
        yield c


def login(client, user):
    r = client.post("/token", data={"username": user, "password": "policylens"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_auth_required_and_bad_password(client):
    assert client.get("/policies").status_code == 401
    assert client.post("/token", data={"username": "alice", "password": "nope"}).status_code == 401


def test_rbac_engineer_cannot_upload_policy_or_approve(client):
    h = login(client, "alice")
    r = client.post("/policies", headers=h, files={"file": ("x.md", b"# X\n## 1 A\nA must b.\n")})
    assert r.status_code == 403
    assert client.post("/approve", headers=h, json={"review_id": 1, "action": "approve"}).status_code == 403


def test_full_workflow_submit_evaluate_approve_package(client):
    eng, rev = login(client, "alice"), login(client, "rita")
    r = client.post("/reviews", headers=eng, json={
        "title": "Customer API", "description": "We are deploying a new API that stores customer information."})
    assert r.status_code == 201
    rid = r.json()["id"]

    r = client.post("/evidence", headers=eng, data={"review_id": rid},
                    files={"file": ("encryption.yaml", b"database: encrypted at rest with AES-256 via KMS\ntls: 1.2")})
    assert r.status_code == 201 and "encryption" in r.json()["detected_types"]
    client.post("/evidence", headers=eng, data={"review_id": rid},
                files={"file": ("logging.yaml", b"audit logging: enabled for all record access\nlog retention: 400 days")})

    controls = client.get(f"/controls?review_id={rid}", headers=eng).json()
    assert controls and all("§" in c["citation"] for c in controls)

    # Cannot decide before evaluation.
    assert client.post("/approve", headers=rev, json={"review_id": rid, "action": "approve"}).status_code == 409

    review = client.post("/evaluate", headers=eng, json={"review_id": rid}).json()
    assert review["status"] == "evaluated" and review["result"] == "Needs Review"
    assert "retention configuration" in review["evidence_requested"]
    for f in review["findings"]:
        assert f["status"] != "PASS" or f["evidence_ids"]

    # Approving with open findings needs a justification.
    r = client.post("/approve", headers=rev, json={"review_id": rid, "action": "approve"})
    assert r.status_code == 422
    r = client.post("/approve", headers=rev, json={"review_id": rid, "action": "return", "comment": ""})
    assert r.status_code == 422
    r = client.post("/approve", headers=rev, json={"review_id": rid, "action": "return",
                                                   "comment": "Provide retention and IAM configuration."})
    assert r.json()["status"] == "returned"

    pkg = client.get(f"/audit/{rid}", headers=rev).json()
    for key in ("executive_summary", "control_matrix", "evidence_references", "open_questions",
                "risk_register", "reviewer_checklist"):
        assert key in pkg
    md = client.get(f"/audit/{rid}?format=md", headers=rev).text
    assert "## Control matrix" in md and "## Reviewer checklist" in md

    log = client.get("/audit-log", headers=rev).json()
    actions = {a["action"] for a in log}
    assert {"review.submit", "evidence.add", "review.evaluate", "review.return", "audit.package"} <= actions


def test_evidence_is_encrypted_at_rest_and_downloadable(client):
    eng = login(client, "alice")
    rid = client.post("/reviews", headers=eng, json={"title": "Enc test", "description": "Add a new logging pipeline."}).json()["id"]
    secret = b"kms_key: alias/super-secret-marker"
    eid = client.post("/evidence", headers=eng, data={"review_id": rid}, files={"file": ("kms.yaml", secret)}).json()["id"]
    from backend.db import Evidence, SessionLocal

    with SessionLocal() as s:
        path = s.get(Evidence, eid).path
    assert b"super-secret-marker" not in open(path, "rb").read()
    assert client.get(f"/evidence/{eid}/download", headers=eng).content == secret


def test_reviewer_cannot_approve_own_request(client):
    adm = login(client, "admin")
    rid = client.post("/reviews", headers=adm, json={"title": "Own", "description": "Change rollback plan for deploy."}).json()["id"]
    client.post("/evaluate", headers=adm, json={"review_id": rid})
    r = client.post("/approve", headers=adm, json={"review_id": rid, "action": "reject", "comment": "Not ready for production."})
    assert r.status_code == 403
