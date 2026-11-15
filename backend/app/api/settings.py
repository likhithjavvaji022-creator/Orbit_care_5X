"""/api/settings, POST /api/simulate/assess. Settings persist in the settings table."""
import copy
import json
import math
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..engine.config import DEFAULT_CONFIG, DEFAULT_WEIGHTS
from ..engine.grading import assess
from ..models import Mission, Setting

router = APIRouter(prefix="/api", tags=["settings"])

DEFAULT_MISSION = {"name": "ORBITCARE Demo Mission", "start": "2026-11-01T00:00:00Z", "planned_days": 180}
KEYS = ("weights", "thresholds", "mission")


def default_thresholds() -> dict:
    return {g: {k: v["value"] for k, v in d.items()} for g, d in DEFAULT_CONFIG.items()}


def _load(db: Session, key: str, default):
    row = db.get(Setting, key)
    if row is None or not row.value:
        return copy.deepcopy(default)
    try:
        v = json.loads(row.value)
    except ValueError:
        return copy.deepcopy(default)
    if isinstance(default, dict) and isinstance(v, dict):
        out = copy.deepcopy(default)
        for k, x in v.items():
            if isinstance(x, dict) and isinstance(out.get(k), dict):
                out[k].update(x)
            else:
                out[k] = x
        return out
    return v


def get_settings(db: Session) -> dict:
    return {"weights": _load(db, "weights", DEFAULT_WEIGHTS),
            "thresholds": _load(db, "thresholds", default_thresholds()),
            "mission": _load(db, "mission", DEFAULT_MISSION)}


def build_cfg(thresholds: dict) -> dict:
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    for g, d in thresholds.items():
        for k, v in d.items():
            if g in cfg and k in cfg[g]:
                cfg[g][k] = dict(cfg[g][k], value=v)
    return cfg


def effective(db: Session):
    """(cfg, weights, mission) used for new assessments."""
    s = get_settings(db)
    return build_cfg(s["thresholds"]), s["weights"], s["mission"]


def _isnum(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _validate(body: dict) -> dict:
    out = {}
    if "weights" in body:
        w = body["weights"]
        if not isinstance(w, dict) or set(w) != set(DEFAULT_WEIGHTS) or not all(_isnum(x) and x >= 0 for x in w.values()):
            raise HTTPException(422, "weights must contain exactly: " + ", ".join(DEFAULT_WEIGHTS) + " (non-negative numbers)")
        if abs(sum(w.values()) - 1.0) > 1e-6:
            raise HTTPException(422, f"weights must sum to 1.0 (got {round(sum(w.values()), 6)})")
        out["weights"] = {k: float(w[k]) for k in DEFAULT_WEIGHTS}
    if "thresholds" in body:
        t = body["thresholds"]
        base = default_thresholds()
        if not isinstance(t, dict):
            raise HTTPException(422, "thresholds must be an object")
        for g, d in t.items():
            if g not in base or not isinstance(d, dict):
                raise HTTPException(422, f"unknown threshold group: {g}")
            for k, v in d.items():
                if k not in base[g]:
                    raise HTTPException(422, f"unknown threshold: {g}.{k}")
                if not _isnum(v):
                    raise HTTPException(422, f"threshold {g}.{k} must be a number")
        out["thresholds"] = t
    if "mission" in body:
        m = body["mission"]
        if not isinstance(m, dict):
            raise HTTPException(422, "mission must be an object")
        pd = m.get("planned_days", DEFAULT_MISSION["planned_days"])
        if not isinstance(pd, int) or isinstance(pd, bool) or pd < 1:
            raise HTTPException(422, "mission.planned_days must be an integer >= 1")
        name = str(m.get("name") or "").strip()
        if not name or len(name) > 120:
            raise HTTPException(422, "mission.name is required (max 120 chars)")
        start = str(m.get("start") or "")
        from datetime import datetime
        try:
            datetime.fromisoformat(start.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(422, "mission.start must be an ISO-8601 timestamp")
        out["mission"] = {"name": name, "start": start, "planned_days": pd}
    return out


def save_settings(db: Session, vals: dict):
    for k, v in vals.items():
        row = db.get(Setting, k)
        if row is None:
            db.add(Setting(key=k, value=json.dumps(v)))
        else:
            row.value = json.dumps(v)


@router.get("/settings")
def read_settings(db: Session = Depends(get_db)):
    return get_settings(db)


@router.put("/settings")
def write_settings(body: dict[str, Any], db: Session = Depends(get_db)):
    vals = _validate(body)
    save_settings(db, vals)
    if 'mission' in vals:  # stage 2 validates against the missions table
        m = db.query(Mission).order_by(Mission.id).first()
        if m is None:
            db.add(Mission(name=vals['mission']['name'], start=vals['mission']['start']))
        else:
            m.name, m.start = vals['mission']['name'], vals['mission']['start']
    db.commit()
    return get_settings(db)


class SimBody(BaseModel):
    row: dict[str, Any]
    day1_score: float | None = None


@router.post("/simulate/assess")
def simulate_assess(body: SimBody, db: Session = Depends(get_db)):
    """What-if assessment of a posted row with current settings. Never stored."""
    cfg, weights, _ = effective(db)
    row = dict(body.row)
    row["source"] = "SIMULATED"
    a = assess(row, cfg, weights, body.day1_score)
    a["simulated"] = True
    return a

