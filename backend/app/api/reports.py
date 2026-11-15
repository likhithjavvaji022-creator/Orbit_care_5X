"""/api/reports/assessments.csv, /api/backup, /api/restore."""
import csv
import io
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AlertRecord, Astronaut, AssessmentRecord, HealthRecord, Mission, Setting
from ..pipeline.runner import reset_reports

router = APIRouter(prefix="/api", tags=["reports"])

DIVS = ["radiation", "mental_health", "gravity", "life_support", "earth_distance"]
TABLES = {"astronauts": Astronaut, "health_records": HealthRecord, "assessments": AssessmentRecord,
          "alerts": AlertRecord, "settings": Setting, "missions": Mission}
ORDER = ["missions", "astronauts", "health_records", "assessments", "alerts", "settings"]


def _cell(s):
    """Neutralise spreadsheet formula injection."""
    s = "" if s is None else str(s)
    return "'" + s if s[:1] in ("=", "+", "-", "@") and not s.replace(".", "", 1).lstrip("-").isdigit() else s


@router.get("/reports/assessments.csv")
def assessments_csv(astronaut_id: str | None = None, db: Session = Depends(get_db)):
    q = select(AssessmentRecord).order_by(AssessmentRecord.timestamp, AssessmentRecord.id)
    if astronaut_id:
        q = q.where(AssessmentRecord.astronaut_id == astronaut_id)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    head = ["astronaut_id", "timestamp", "mission_day", "scenario_id", "source"]
    for d in DIVS:
        head += [f"{d}_score", f"{d}_status"]
    head += ["total_score", "total_grade", "total_status", "penalty", "capped", "delta_from_day1"]
    w.writerow(head)
    for r in db.execute(q).scalars():
        p = r.payload
        row = [_cell(r.astronaut_id), r.timestamp, r.mission_day, p.get("scenario_id"), p.get("source")]
        for d in DIVS:
            dv = (p.get("divisions") or {}).get(d) or {}
            row += [dv.get("score"), dv.get("status")]
        t = p.get("total") or {}
        row += [t.get("score"), t.get("grade"), t.get("status"), t.get("penalty"), int(bool(t.get("capped"))), t.get("delta_from_day1")]
        w.writerow(row)
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="orbitcare_assessments.csv"'})


def _dump(obj) -> dict:
    out = {}
    for c in obj.__table__.columns:
        v = getattr(obj, c.name)
        out[c.name] = v.isoformat() if isinstance(v, datetime) else v
    return out


@router.get("/backup")
def backup(db: Session = Depends(get_db)):
    data = {name: [_dump(o) for o in db.execute(select(TABLES[name])).scalars()] for name in ORDER}
    return Response(__import__("json").dumps({"app": "ORBITCARE 5X", "version": 1, "tables": data}),
                    media_type="application/json",
                    headers={"Content-Disposition": 'attachment; filename="orbitcare_backup.json"'})


@router.post("/restore")
def restore(body: dict[str, Any], db: Session = Depends(get_db)):
    tables = body.get("tables") if isinstance(body, dict) else None
    if not isinstance(tables, dict) or body.get("app") != "ORBITCARE 5X":
        raise HTTPException(400, "not an ORBITCARE 5X backup file")
    try:
        objs = []
        for name in ORDER:
            model = TABLES[name]
            cols = {c.name: c for c in model.__table__.columns}
            for rec in tables.get(name, []):
                kw = {}
                for k, v in rec.items():
                    if k not in cols:
                        continue
                    if v is not None and cols[k].type.python_type is datetime:
                        v = datetime.fromisoformat(v)
                    kw[k] = v
                objs.append(model(**kw))
        for name in reversed(ORDER):
            db.execute(delete(TABLES[name]))
        db.add_all(objs)
        db.commit()
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(400, f"restore failed: {type(e).__name__}: {e}")
    reset_reports()
    return {"status": "restored", "counts": {n: len(tables.get(n, [])) for n in ORDER}}
