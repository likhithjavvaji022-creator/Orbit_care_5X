from backend.tests.test_api import client, upload_csv  # noqa: F401


def test_raw_rows(client):
    assert client.get("/api/telemetry", params={"astronaut_id": "SIM-A1"}).json() == {"items": []}
    upload_csv(client)
    items = client.get("/api/telemetry", params={"astronaut_id": "SIM-A1"}).json()["items"]
    assert len(items) == 32
    assert [x["timestamp"] for x in items] == sorted(x["timestamp"] for x in items)
    r = items[0]
    assert r["cabin_temp_c"] is not None and r["cabin_humidity_pct"] is not None
    assert "received_at" in r and r["suspect"] in (True, False) and r["source"] == "SIMULATED"
    assert client.get("/api/telemetry", params={"astronaut_id": "nobody"}).json()["items"] == []


def test_suspect_persisted(client):
    upload_csv(client)
    items = client.get("/api/telemetry").json()["items"]
    sus = [x for x in items if x["suspect"] is True]
    assert sus, "sample contains spikes; some rows must be suspect"
    for x in sus:
        assert x["suspect_metrics"] and all({"metric", "reason"} <= set(m) for m in x["suspect_metrics"])
    assert all(x["suspect_metrics"] == [] for x in items if x["suspect"] is False)
