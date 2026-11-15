import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import noaa

PROTON = [
    {"time_tag": "2026-01-01T00:00:00Z", "satellite": 19, "flux": 0.2, "energy": ">=10 MeV"},
    {"time_tag": "2026-01-01T00:05:00Z", "satellite": 19, "flux": 12.5, "energy": ">=10 MeV"},
    {"time_tag": "2026-01-01T00:05:00Z", "satellite": 19, "flux": 99.0, "energy": ">=50 MeV"},
]
XRAY = [
    {"time_tag": "2026-01-01T00:04:00Z", "satellite": 19, "flux": 1.2e-6, "energy": "0.1-0.8nm"},
    {"time_tag": "2026-01-01T00:04:00Z", "satellite": 19, "flux": 1e-8, "energy": "0.05-0.4nm"},
]
KP = [["time_tag", "Kp", "a_running", "station_count"],
      ["2026-01-01 00:00:00.000", "2.33", "9", "8"],
      ["2026-01-01 03:00:00.000", "4.00", "15", "8"]]
SCALES = {"0": {"DateStamp": "2026-01-01", "TimeStamp": "00:10:00",
                "R": {"Scale": "1", "Text": "minor"}, "S": {"Scale": "1", "Text": "minor"},
                "G": {"Scale": "0", "Text": "none"}}}


def make_handler(state):
    def handler(request: httpx.Request) -> httpx.Response:
        state["calls"] += 1
        if state["fail"]:
            return httpx.Response(500)
        u = str(request.url)
        for key, body in (("integral-protons", PROTON), ("xrays", XRAY),
                          ("planetary-k-index", KP), ("noaa-scales", SCALES)):
            if key in u:
                return httpx.Response(200, json=body)
        return httpx.Response(404)
    return handler


@pytest.fixture()
def sw(monkeypatch):
    state = {"calls": 0, "fail": False, "t": 1000.0}
    noaa.reset_cache()
    monkeypatch.setattr(noaa, "RETRY_DELAY_S", 0)
    monkeypatch.setattr(noaa, "transport_factory",
                        lambda: httpx.MockTransport(make_handler(state)))
    monkeypatch.setattr(noaa, "now", lambda: state["t"])
    monkeypatch.setenv("NOAA_POLL_S", "60")
    with TestClient(app) as c:
        yield c, state
    noaa.reset_cache()


def test_live_then_cached(sw):
    c, st = sw
    j = c.get("/api/spaceweather").json()
    assert j["status"] == "LIVE" and j["error"] is None and j["stale"] is False
    d = j["data"]
    assert d["proton_flux"]["value"] == 12.5 and d["proton_flux"]["sep_active"] is True
    assert "S1" in d["proton_flux"]["sep_label"]
    assert d["xray_flux"]["value"] == 1.2e-6
    assert d["kp"]["value"] == 4.0 and d["kp"]["observed_at"].endswith("Z")
    assert d["scales"]["S"]["scale"] == "1"
    for k in ("proton_flux", "xray_flux", "kp", "scales"):
        assert d[k]["source"].startswith("https://services.swpc.noaa.gov")
        assert d[k]["observed_at"]
    n = st["calls"]
    st["t"] += 10
    j2 = c.get("/api/spaceweather").json()
    assert j2["status"] == "CACHED" and j2["error"] is None and st["calls"] == n


def test_failed_no_cache(sw):
    c, st = sw
    st["fail"] = True
    j = c.get("/api/spaceweather").json()
    assert j["status"] == "FAILED" and j["data"] is None and "500" in j["error"]
    assert j["fetched_at"] is None


def test_failure_with_cache_serves_cached_with_error(sw):
    c, st = sw
    assert c.get("/api/spaceweather").json()["status"] == "LIVE"
    st["fail"] = True
    st["t"] += 120  # past poll interval -> refresh attempted
    j = c.get("/api/spaceweather").json()
    assert j["status"] == "CACHED" and j["error"] and j["data"] is not None


def test_stale_flag_and_force_refresh(sw):
    c, st = sw
    c.get("/api/spaceweather")
    st["fail"] = True
    st["t"] += 31 * 60
    j = c.get("/api/spaceweather").json()
    assert j["status"] == "CACHED" and j["stale"] is True and j["age_s"] > 1800
    st["fail"] = False
    r = c.post("/api/spaceweather/refresh").json()
    assert r["status"] == "LIVE" and r["stale"] is False


def test_real_call_smoke(monkeypatch):
    """Live network call; any contract status is acceptable offline."""
    monkeypatch.setattr(noaa, "transport_factory", lambda: None)
    monkeypatch.setattr(noaa, "RETRY_DELAY_S", 0)
    noaa.reset_cache()
    with TestClient(app) as c:
        j = c.get("/api/spaceweather").json()
    print("REAL STATUS:", j["status"], j["error"])
    assert j["status"] in ("LIVE", "FAILED")
    noaa.reset_cache()
