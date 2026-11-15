import json

import pytest
from fastapi.testclient import TestClient

from backend.app import db
from backend.app.main import app
from backend.tests.test_api import upload_csv


@pytest.fixture()
def client(tmp_path):
    db.configure(f"sqlite:///{tmp_path / 't.db'}")
    db.init_db()
    with TestClient(app) as c:
        yield c
    db.engine.dispose()


def test_settings_defaults_and_validation(client):
    s = client.get("/api/settings").json()
    assert abs(sum(s["weights"].values()) - 1.0) < 1e-9
    assert s["thresholds"]["radiation"]["career_limit_msv"] == 600
    bad = dict(s["weights"], radiation=0.5)
    assert client.put("/api/settings", json={"weights": bad}).status_code == 422
    assert client.put("/api/settings", json={"thresholds": {"nope": {"x": 1}}}).status_code == 422


def test_weights_apply_to_later_assessments(client):
    base = upload_csv(client).json()["assessments"]
    w = {"radiation": 1.0, "life_support": 0, "mental_health": 0, "gravity": 0, "earth_distance": 0}
    assert client.put("/api/settings", json={"weights": w}).status_code == 200
    assert client.get("/api/settings").json()["weights"]["radiation"] == 1.0
    client.delete("/api/telemetry")
    new = upload_csv(client).json()["assessments"]
    a, b = base[-1], new[-1]
    assert b["total"]["weighted"] == b["divisions"]["radiation"]["score"]
    assert a["total"]["weighted"] != b["total"]["weighted"]


def test_simulate_assess_not_stored(client):
    row = {"astronaut_id": "SIM", "mission_day": 5, "cum_dose_msv": 600, "proton_flux_pfu": 20, "flare_active": 1,
           "sleep_h": 8, "fatigue": 0, "stress": 0, "cabin_co2_ppm": 400, "cabin_o2_pct": 21,
           "cabin_pressure_kpa": 101, "scrubber_state": "nominal", "latency_s": 1, "open_medical_flags": 0}
    r = client.post("/api/simulate/assess", json={"row": row})
    assert r.status_code == 200
    j = r.json()
    assert j["divisions"]["radiation"]["score"] == 10.0 and j["total"]["capped"] is True
    assert j["source"] == "SIMULATED"
    assert client.get("/api/assessments").json()["items"] == []


def test_csv_backup_restore(client):
    upload_csv(client)
    r = client.get("/api/reports/assessments.csv")
    lines = r.text.strip().split("\n")
    assert r.headers["content-type"].startswith("text/csv") and len(lines) == 33
    assert lines[0].startswith("astronaut_id,timestamp")
    dump = client.get("/api/backup").json()
    assert len(dump["tables"]["assessments"]) == 32
    client.delete("/api/telemetry")
    assert client.get("/api/assessments").json()["items"] == []
    r = client.post("/api/restore", json=dump)
    assert r.status_code == 200
    assert len(client.get("/api/assessments").json()["items"]) == 32
    assert len(client.get("/api/telemetry").json()["items"]) == 32
    assert client.post("/api/restore", json={"x": 1}).status_code == 400


def test_mission_saved(client):
    m = {"name": "Test", "start": "2026-11-01T00:00:00Z", "planned_days": 30}
    assert client.put("/api/settings", json={"mission": m}).json()["mission"] == m
    assert client.put("/api/settings", json={"mission": dict(m, planned_days=0)}).status_code == 422
