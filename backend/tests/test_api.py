import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import db
from backend.app.main import app

SAMPLE = Path(__file__).resolve().parents[2] / "data" / "sample"


@pytest.fixture()
def client(tmp_path):
    db.configure(f"sqlite:///{tmp_path / 'test.db'}")
    db.init_db()
    with TestClient(app) as c:
        yield c
    db.engine.dispose()


def upload_csv(c):
    data = (SAMPLE / "workflow_a_31_scenarios.csv").read_bytes()
    return c.post("/api/telemetry/upload", files={"file": ("s.csv", data, "text/csv")})


def test_upload_sample_csv(client):
    r = upload_csv(client)
    assert r.status_code == 200
    j = r.json()
    assert j["received"] == 32 and j["accepted"] == 32 and j["rejected"] == []
    a = j["assessments"]
    assert a[0]["total"]["score"] >= 95 and a[0]["total"]["grade"] == "A+"
    full = [x for x in a if x["scenario_id"] == 31][0]
    assert full["total"]["capped"] is True and full["total"]["grade"] in ("D", "F")
    assert len(j["pipeline"]) == 7
    traj = client.get("/api/assessments", params={"astronaut_id": "SIM-A1"}).json()["items"]
    assert len(traj) == 32
    assert [x["timestamp"] for x in traj] == sorted(x["timestamp"] for x in traj)
    assert len(client.get("/api/assessments/latest").json()["items"]) == 1
    assert client.get("/api/crew").json()["items"][0]["astronaut_id"] == "SIM-A1"
    alerts = client.get("/api/alerts").json()["items"]
    assert alerts and any(x["severity"] == "critical" for x in alerts)
    keys = [(x["astronaut_id"], x["code"], x["day"]) for x in alerts]
    assert len(keys) == len(set(keys))


def test_reupload_all_duplicates(client):
    upload_csv(client)
    j = upload_csv(client).json()
    assert j["accepted"] == 0 and len(j["rejected"]) == 32
    assert all("duplicate" in x["reason"] for x in j["rejected"])


def test_json_ingest_and_upload_json(client):
    rows = json.loads((SAMPLE / "workflow_a_31_scenarios.json").read_text())["rows"]
    j = client.post("/api/telemetry/ingest", json={"rows": rows[:3]}).json()
    assert j["accepted"] == 3
    r = client.post("/api/telemetry/upload",
                    files={"file": ("s.json", json.dumps({"rows": rows[3:6]}), "application/json")})
    assert r.json()["accepted"] == 3
    assert client.post("/api/telemetry/upload", files={"file": ("x.txt", b"hi")}).status_code == 400


def test_future_timestamp_rejected(client):
    row = client.get("/api/telemetry/simulate", params={"day": 1}).json()
    row["source"] = "USER-ENTERED"
    row["timestamp"] = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    j = client.post("/api/telemetry/ingest", json={"rows": [row]}).json()
    assert j["accepted"] == 0 and "future" in j["rejected"][0]["reason"]


def test_range_rejected(client):
    row = client.get("/api/telemetry/simulate").json()
    row["fatigue"] = 42
    j = client.post("/api/telemetry/ingest", json={"rows": [row]}).json()
    assert j["accepted"] == 0 and "fatigue" in j["rejected"][0]["reason"]


def test_simulate_and_reset(client):
    row = client.get("/api/telemetry/simulate", params={"astronaut_id": "SIM-A1", "day": 5, "scenario_id": 31}).json()
    assert row["source"] == "SIMULATED" and row["scenario_id"] == 31 and row["mission_day"] == 5
    assert client.get("/api/assessments").json()["items"] == []
    upload_csv(client)
    assert client.delete("/api/telemetry").status_code == 200
    assert client.get("/api/assessments").json()["items"] == []
    assert client.get("/api/crew").json()["items"] == []


def test_pipeline_status_and_health(client):
    assert client.get("/api/health").json()["status"] == "ok"
    upload_csv(client)
    st = client.get("/api/pipeline/status").json()["stages"]
    assert [s["stage"] for s in st] == [1, 2, 3, 4, 5, 6, 7]
    assert st[1]["records_out"] == 32 and st[4]["records_out"] == 32
