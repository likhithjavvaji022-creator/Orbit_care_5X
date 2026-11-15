"""/api/assessments, /api/crew, /api/alerts, /api/pipeline/status."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AlertRecord, Astronaut, AssessmentRecord
from ..pipeline.runner import status_reports

router = APIRouter(prefix="/api", tags=["assessments"])


@router.get("/assessments/latest")
def latest(db: Session = Depends(get_db)):
    ids = db.execute(select(AssessmentRecord.astronaut_id).distinct().order_by(AssessmentRecord.astronaut_id)).scalars().all()
    items = []
    for aid in ids:
        rec = db.execute(select(AssessmentRecord).where(AssessmentRecord.astronaut_id == aid)
                         .order_by(AssessmentRecord.timestamp.desc()).limit(1)).scalars().first()
        items.append(rec.payload)
    return {"items": items}


@router.get("/assessments")
def assessments(astronaut_id: str | None = None, db: Session = Depends(get_db)):
    q = select(AssessmentRecord).order_by(AssessmentRecord.timestamp, AssessmentRecord.id)
    if astronaut_id:
        q = q.where(AssessmentRecord.astronaut_id == astronaut_id)
    return {"items": [r.payload for r in db.execute(q).scalars()]}


@router.get("/pipeline/status")
def pipeline_status():
    return {"stages": status_reports()}


@router.get("/crew")
def crew(db: Session = Depends(get_db)):
    rows = db.execute(select(Astronaut).order_by(Astronaut.astronaut_id)).scalars().all()
    return {"items": [{"astronaut_id": a.astronaut_id, "name": a.name, "source": "SIMULATED"} for a in rows]}


@router.get("/alerts")
def alerts(db: Session = Depends(get_db)):
    rows = db.execute(select(AlertRecord).order_by(AlertRecord.id)).scalars().all()
    return {"items": [{"id": a.id, "astronaut_id": a.astronaut_id, "severity": a.severity,
                       "code": a.code, "message": a.message,
                       "created_at": a.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"), "day": a.day}
                      for a in rows]}
