import uuid

import pytest
from fastapi.testclient import TestClient

from api.main import app

GOOD = "correct-horse-42"


@pytest.fixture(scope="module")
def client(seeded):
    with TestClient(app) as c:
        yield c


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def login(client, username, password="policylens"):
    r = client.post("/token", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def new_user(client, **extra):
    name = "u" + uuid.uuid4().hex[:8]
    r = client.post("/register", json={"username": name, "password": GOOD, **extra})
    assert r.status_code == 201, r.text
    return name, r.json()["access_token"]


def test_register_creates_engineer_and_enforces_rules(client):
    name, token = new_user(client, display_name="Sam Lee", email="sam@example.com")
    me = client.get("/me", headers=auth(token)).json()
    assert me["role"] == "engineer" and me["display_name"] == "Sam Lee" and not me["is_demo"]

    assert client.post("/register", json={"username": name, "password": GOOD}).status_code == 409
    assert client.post("/register", json={"username": "Bad Name!", "password": GOOD}).status_code == 422
    r = client.post("/register", json={"username": "shorty" + uuid.uuid4().hex[:4], "password": "abc"})
    assert r.status_code == 422 and "10 characters" in r.json()["detail"]
    r = client.post("/register", json={"username": "x" + uuid.uuid4().hex[:6], "password": GOOD, "email": "nope"})
    assert r.status_code == 422


def test_profile_update(client):
    _, token = new_user(client)
    r = client.patch("/me", headers=auth(token), json={"display_name": "  New Name ", "email": "new@example.com"})
    assert r.json()["display_name"] == "New Name" and r.json()["email"] == "new@example.com"


def test_change_password_signs_out_other_sessions(client):
    name, old_token = new_user(client)
    assert client.post("/me/password", headers=auth(old_token),
                       json={"current_password": "wrong", "new_password": "another-pass-77"}).status_code == 400
    r = client.post("/me/password", headers=auth(old_token),
                    json={"current_password": GOOD, "new_password": "another-pass-77"})
    assert r.status_code == 200
    assert client.get("/me", headers=auth(old_token)).status_code == 401  # old session ended
    assert client.get("/me", headers=auth(r.json()["access_token"])).status_code == 200
    login(client, name, "another-pass-77")


def test_sign_out_everywhere(client):
    _, token = new_user(client)
    fresh = client.post("/me/sign-out-everywhere", headers=auth(token)).json()["access_token"]
    assert client.get("/me", headers=auth(token)).status_code == 401
    assert client.get("/me", headers=auth(fresh)).status_code == 200


def test_demo_accounts_cannot_change_password(client):
    token = login(client, "alice")
    r = client.post("/me/password", headers=auth(token),
                    json={"current_password": "policylens", "new_password": "hijack-pass-99"})
    assert r.status_code == 403


def test_dashboard_shapes_by_role(client):
    eng = client.get("/dashboard", headers=auth(login(client, "alice"))).json()
    rev = client.get("/dashboard", headers=auth(login(client, "rita"))).json()
    assert eng["me"]["username"] == "alice" and eng["decision_queue"] == []
    assert set(rev["counts"]) >= {"my_open", "awaiting_decision", "approved", "policies"}
    assert rev["counts"]["policies"] == 9


def test_admin_manages_users(client):
    name, token = new_user(client)
    adm = auth(login(client, "admin"))
    users = client.get("/users", headers=adm).json()
    uid = next(u["id"] for u in users if u["username"] == name)
    assert client.get("/users", headers=auth(token)).status_code == 403

    assert client.patch(f"/users/{uid}", headers=adm, json={"role": "reviewer"}).json()["role"] == "reviewer"
    temp = client.post(f"/users/{uid}/reset-password", headers=adm).json()["temporary_password"]
    assert client.get("/me", headers=auth(token)).status_code == 401  # reset ends sessions
    login(client, name, temp)

    client.patch(f"/users/{uid}", headers=adm, json={"is_active": False})
    assert client.post("/token", data={"username": name, "password": temp}).status_code == 403

    admin_id = next(u["id"] for u in users if u["username"] == "admin")
    assert client.patch(f"/users/{admin_id}", headers=adm, json={"is_active": False}).status_code == 409
