"""SQLAlchemy 2 models (PLAN section 7 subset used by the pipeline)."""
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def _now():
    return datetime.now(timezone.utc)


class Mission(Base):
    __tablename__ = "missions"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    start: Mapped[str] = mapped_column(String(32))  # ISO UTC


class Astronaut(Base):
    __tablename__ = "astronauts"
    astronaut_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    source: Mapped[str] = mapped_column(String(16), default="SIMULATED")


class HealthRecord(Base):
    """One ingested telemetry row (CONTRACT section 2)."""
    __tablename__ = "health_records"
    __table_args__ = (UniqueConstraint("astronaut_id", "timestamp", name="uq_astro_ts"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[str] = mapped_column(String(32), index=True)
    astronaut_id: Mapped[str] = mapped_column(String(64), index=True)
    mission_day: Mapped[int] = mapped_column(Integer)
    scenario_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scenario_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cum_dose_msv: Mapped[float | None] = mapped_column(Float, nullable=True)
    proton_flux_pfu: Mapped[float | None] = mapped_column(Float, nullable=True)
    flare_active: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    sleep_h: Mapped[float | None] = mapped_column(Float, nullable=True)
    hrv_rmssd_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    hrv_baseline_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    fatigue: Mapped[float | None] = mapped_column(Float, nullable=True)
    stress: Mapped[float | None] = mapped_column(Float, nullable=True)
    loading_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    loading_target: Mapped[float | None] = mapped_column(Float, nullable=True)
    balance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    cabin_o2_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    cabin_co2_ppm: Mapped[float | None] = mapped_column(Float, nullable=True)
    cabin_pressure_kpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    cabin_temp_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    cabin_humidity_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    scrubber_state: Mapped[str | None] = mapped_column(String(16), nullable=True)
    latency_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    open_medical_flags: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(16))
    suspect_metrics: Mapped[list | None] = mapped_column(JSON, nullable=True)  # None = stored pre-fix/unknown
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AssessmentRecord(Base):
    __tablename__ = "assessments"
    id: Mapped[int] = mapped_column(primary_key=True)
    astronaut_id: Mapped[str] = mapped_column(String(64), index=True)
    timestamp: Mapped[str] = mapped_column(String(32), index=True)
    mission_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    grade: Mapped[str | None] = mapped_column(String(4), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON)  # full Assessment


class AlertRecord(Base):
    __tablename__ = "alerts"
    __table_args__ = (UniqueConstraint("astronaut_id", "code", "day", name="uq_alert_day"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    astronaut_id: Mapped[str] = mapped_column(String(64), index=True)
    severity: Mapped[str] = mapped_column(String(16))
    code: Mapped[str] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(String(400))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    day: Mapped[int] = mapped_column(Integer)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str | None] = mapped_column(String(400), nullable=True)


_checked: set = set()


def ensure_suspect_column(session):
    """Tiny dev migration: add health_records.suspect_metrics to pre-existing SQLite DBs."""
    from sqlalchemy import text
    bind = session.get_bind()
    if id(bind) in _checked:
        return
    cols = [r[1] for r in session.execute(text("PRAGMA table_info(health_records)"))]
    if cols and "suspect_metrics" not in cols:
        session.execute(text("ALTER TABLE health_records ADD COLUMN suspect_metrics JSON"))
        session.commit()
    _checked.add(id(bind))
