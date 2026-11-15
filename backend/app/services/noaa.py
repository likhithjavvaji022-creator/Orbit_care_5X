"""NOAA SWPC live space-weather client with in-memory cache.

Never fabricates values and never converts flux to dose. Each field carries
its own source URL and observed_at timestamp.
"""
import asyncio
import os
import time
from datetime import datetime, timezone
from typing import Any, Callable, Optional

import httpx

BASE = "https://services.swpc.noaa.gov"
URL_PROTON = f"{BASE}/json/goes/primary/integral-protons-1-day.json"
URL_XRAY = f"{BASE}/json/goes/primary/xrays-1-day.json"
URL_KP = f"{BASE}/products/noaa-planetary-k-index.json"
URL_SCALES = f"{BASE}/products/noaa-scales.json"

TIMEOUT_S = 10.0
RETRIES = 2
RETRY_DELAY_S = 0.5
STALE_AFTER_S = 30 * 60
SEP_THRESHOLD_PFU = 10.0

# Module-level factory so tests can inject an httpx.MockTransport.
transport_factory: Callable[[], Optional[httpx.AsyncBaseTransport]] = lambda: None
# Module-level clock so tests can age the cache.
now: Callable[[], float] = time.time

_cache: dict[str, Any] = {"data": None, "fetched_at": None}  # fetched_at: epoch seconds
_lock: Optional[asyncio.Lock] = None


def poll_interval_s() -> float:
    try:
        return float(os.environ.get("NOAA_POLL_S", "60"))
    except ValueError:
        return 60.0


def reset_cache() -> None:
    _cache["data"] = None
    _cache["fetched_at"] = None


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()


def _norm_time(s: Optional[str]) -> Optional[str]:
    """NOAA timestamps are UTC, often without a zone suffix."""
    if not s:
        return None
    return s if s.endswith("Z") or "+" in s[10:] else s + "Z"


async def _get_json(client: httpx.AsyncClient, url: str) -> Any:
    last: Exception = RuntimeError("no attempt")
    for attempt in range(RETRIES + 1):
        try:
            r = await client.get(url)
            r.raise_for_status()
            return r.json()
        except (httpx.HTTPError, ValueError) as e:
            last = e
            if attempt < RETRIES:
                await asyncio.sleep(RETRY_DELAY_S * (attempt + 1))
    detail = (f"HTTP {last.response.status_code}" if isinstance(last, httpx.HTTPStatusError)
              else f"{type(last).__name__}: {last}".strip(": "))
    raise RuntimeError(f"{url} failed after {RETRIES + 1} attempts ({detail})")


def _latest_proton(rows: list) -> dict:
    cands = [r for r in rows if str(r.get("energy", "")).replace(" ", "") == ">=10MeV"
             and r.get("flux") is not None]
    if not cands:
        raise RuntimeError("no >=10 MeV proton flux in NOAA response")
    r = max(cands, key=lambda x: x["time_tag"])
    flux = float(r["flux"])
    return {"value": flux, "unit": "pfu", "energy": ">=10 MeV", "satellite": r.get("satellite"),
            "observed_at": _norm_time(r["time_tag"]), "source": URL_PROTON,
            "sep_active": flux >= SEP_THRESHOLD_PFU,
            "sep_threshold_pfu": SEP_THRESHOLD_PFU,
            "sep_label": "NOAA S1 threshold (>=10 pfu at >=10 MeV)"}


def _latest_xray(rows: list) -> dict:
    cands = [r for r in rows if r.get("energy") == "0.1-0.8nm" and r.get("flux") is not None]
    if not cands:
        raise RuntimeError("no long-band X-ray flux in NOAA response")
    r = max(cands, key=lambda x: x["time_tag"])
    return {"value": float(r["flux"]), "unit": "W/m^2", "band": "0.1-0.8nm",
            "satellite": r.get("satellite"), "observed_at": _norm_time(r["time_tag"]),
            "source": URL_XRAY}


def _latest_kp(rows: list) -> dict:
    if not rows:
        raise RuntimeError("empty Kp response")
    if isinstance(rows[0], list):  # legacy: header row + list rows
        head = rows[0]
        recs = [dict(zip(head, r)) for r in rows[1:]]
    elif isinstance(rows[0], dict):  # current: list of objects
        recs = rows
    else:
        raise RuntimeError("unexpected Kp response shape")
    recs = [r for r in recs if r.get("time_tag") and r.get("Kp", r.get("kp_index")) is not None]
    if not recs:
        raise RuntimeError("no Kp values in NOAA response")
    rec = max(recs, key=lambda x: x["time_tag"])
    kp = rec.get("Kp", rec.get("kp_index"))
    return {"value": float(kp), "observed_at": _norm_time(rec["time_tag"]), "source": URL_KP}

def _scales(obj: dict) -> dict:
    cur = obj.get("0")
    if not isinstance(cur, dict):
        raise RuntimeError("unexpected NOAA scales response shape")
    out = {"source": URL_SCALES,
           "observed_at": _norm_time(f"{cur.get('DateStamp')}T{cur.get('TimeStamp')}")
           if cur.get("DateStamp") and cur.get("TimeStamp") else None}
    for k in ("R", "S", "G"):
        v = cur.get(k) or {}
        out[k] = {"scale": v.get("Scale"), "text": v.get("Text")}
    return out


async def _fetch_all() -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT_S, transport=transport_factory()) as c:
        p, x, k, s = await asyncio.gather(
            _get_json(c, URL_PROTON), _get_json(c, URL_XRAY),
            _get_json(c, URL_KP), _get_json(c, URL_SCALES), return_exceptions=True)
    errs = [str(e) for e in (p, x, k, s) if isinstance(e, Exception)]
    if errs:
        raise RuntimeError("; ".join(errs))
    return {"proton_flux": _latest_proton(p), "xray_flux": _latest_xray(x),
            "kp": _latest_kp(k), "scales": _scales(s)}


def _response(status: str, error: Optional[str]) -> dict:
    fa = _cache["fetched_at"]
    age = None if fa is None else max(0.0, now() - fa)
    return {"status": status,
            "fetched_at": None if fa is None else _iso(fa),
            "age_s": None if age is None else round(age, 1),
            "stale": bool(age is not None and age > STALE_AFTER_S),
            "error": error,
            "data": _cache["data"]}


async def get_spaceweather(force: bool = False) -> dict:
    global _lock
    if _lock is None:
        _lock = asyncio.Lock()
    async with _lock:
        fa = _cache["fetched_at"]
        if not force and fa is not None and now() - fa < poll_interval_s():
            return _response("CACHED", None)
        try:
            data = await _fetch_all()
        except Exception as e:  # noqa: BLE001 - reported to caller, never swallowed silently
            err = str(e) or type(e).__name__
            if _cache["data"] is not None:
                return _response("CACHED", err)
            return _response("FAILED", err)
        _cache["data"], _cache["fetched_at"] = data, now()
        return _response("LIVE", None)

