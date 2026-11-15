from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_null_origin_get_allowed():
    r = client.get("/api/health", headers={"Origin": "null"})
    assert r.headers.get("access-control-allow-origin") == "null"
    assert "access-control-allow-credentials" not in r.headers


def test_null_origin_preflight_allowed():
    r = client.options(
        "/api/health",
        headers={"Origin": "null", "Access-Control-Request-Method": "GET"},
    )
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "null"


def test_evil_origin_denied():
    r = client.get("/api/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in r.headers
    r = client.options(
        "/api/health",
        headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in r.headers
