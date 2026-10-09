import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client(seeded, tmp_path_factory):
    site = tmp_path_factory.mktemp("dist")
    (site / "index.html").write_text("<html>policylens</html>")
    os.environ["STATIC_DIR"] = str(site)
    import importlib

    import api.server

    importlib.reload(api.server)
    with TestClient(api.server.app) as c:
        yield c


def test_api_is_served_under_api_prefix(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    r = client.post("/api/token", data={"username": "alice", "password": "policylens"})
    assert r.status_code == 200


def test_site_and_client_routes_serve_index(client):
    assert "policylens" in client.get("/").text
    assert "policylens" in client.get("/reviews/3").text
