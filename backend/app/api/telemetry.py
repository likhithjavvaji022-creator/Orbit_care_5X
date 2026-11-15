"""/api/telemetry/* endpoints."""
import csv
import importlib.util
import io
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import ensure_suspect_column, AlertRecord, Astronaut, AssessmentRecord, HealthRecord
from ..pipeline.runner import reset_reports, run_pipeline

router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])

GEN_PATH = Path(__file__).resolve().parents[3] / "scripts" / "generate_sample.py"
_gen = None


def _generator():
    global _gen
    if _gen is None:
        spec = importlib.util.spec_from_file_location("generate_sample", GEN_PATH)
        _gen = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_gen)
    return _gen


class IngestBody(BaseModel):
    rows: list[dict[str, Any]]


def _parse_upload(name: str, data: bytes) -> list:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(400, "file must be UTF-8 text")
    lower = (name or "").lower()
    if lower.endswith(".json"):
        try:
            obj = json.loads(text)
        except ValueError as e:
            raise HTTPException(400, f"invalid JSON: {e}")
        rows = obj.get("rows") if isinstance(obj, dict) else obj
        if not isinstance(rows, list):
            raise HTTPException(400, "JSON must be a list of rows or {\"rows\": [...]}")
        return rows
    if lower.endswith(".csv"):
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            raise HTTPException(400, "CSV has no header")
        return [dict(r) for r in reader]
    raise HTTPException(400, "unsupported file type; upload .csv or .json")


@router.post("/upload")
async def upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    rows = _parse_upload(file.filename, await file.read())
    return run_pipeline(db, rows, default_source="USER-ENTERED")


@router.post("/ingest")
def ingest(body: IngestBody, db: Session = Depends(get_db)):
    return run_pipeline(db, body.rows, default_source="USER-ENTERED")


@router.get("/simulate")
def simulate(astronaut_id: str = "SIM-A1", day: int = Query(1, ge=1),
             scenario_id: int | None = Query(None, ge=0, le=31)):
    g = _generator()
    if scenario_id is None:
        seq = g.scenario_sequence()
        scenario_id = seq[(day - 1) % len(seq)]
    cum = g.BASE_DOSE_MSV + g.DOSE_PER_DAY_MSV * (day - 1) + (g.DOSE_PER_RADIATION_DAY_MSV if scenario_id & 1 else 0)
    return g.make_row(astronaut_id, day, scenario_id, round(cum, 2))


@router.get("")
def list_raw(astronaut_id: str | None = None, db: Session = Depends(get_db)):
    """Stored raw rows (CONTRACT section 4). `suspect` is null for rows stored before suspect flags were persisted."""
    ensure_suspect_column(db)
    q = select(HealthRecord).order_by(HealthRecord.timestamp, HealthRecord.id)
    if astronaut_id:
        q = q.where(HealthRecord.astronaut_id == astronaut_id)
    items = []
    for r in db.execute(q).scalars():
        d = {c.name: getattr(r, c.name) for c in HealthRecord.__table__.columns if c.name not in ("id", "received_at", "suspect_metrics")}
        d["received_at"] = r.received_at.isoformat() if r.received_at else None
        sm = r.suspect_metrics
        d["suspect"] = None if sm is None else bool(sm)
        d["suspect_metrics"] = sm
        items.append(d)
    return {"items": items}


@router.delete("")
def reset(db: Session = Depends(get_db)):
    counts = {}
    for model in (AlertRecord, AssessmentRecord, HealthRecord, Astronaut):
        counts[model.__tablename__] = db.execute(delete(model)).rowcount
    db.commit()
    reset_reports()
    return {"status": "reset", "deleted": counts}

