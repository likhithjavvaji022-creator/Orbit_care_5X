# ORBITCARE 5X — Complete Consolidated Repository Codebase
> Repository: https://github.com/likhithjavvaji022-creator/Orbit_care_5X.git
> All source files consolidated into a single document.

## File: requirements.txt

`text
fastapi
uvicorn[standard]
sqlalchemy>=2
pydantic>=2
httpx
pandas
numpy
python-multipart
pytest
`

## File: Dockerfile

`
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
`

## File: .env.example

`
DATABASE_URL=sqlite:///./orbitcare.db
NOAA_POLL_S=60
DONKI_POLL_S=300
OSDR_POLL_S=600
NASA_API_KEY=DEMO_KEY

# Comma-separated browser origins allowed by CORS (no wildcard).
# "null" allows file:// pages (the single-file dist build); REMOVE it for any shared deployment.
CORS_ORIGINS=null,http://localhost:8090,http://127.0.0.1:8090
`

## File: docs/CONTRACT.md

`markdown
# ORBITCARE 5X — Interface Contract (source of truth for all workers)

PLAN.md Section 3 guardrails override this file. Stack: Python 3.11+, FastAPI, SQLAlchemy 2, Pydantic v2, httpx, Pandas, NumPy, SQLite; vanilla JS ES modules + Chart.js 4 vendored (no CDN at runtime, no build step).

## 1. Folder layout (one owner per file per milestone)
```
backend/app/main.py            FastAPI app, mounts /api routers, serves frontend/ at /
backend/app/db.py              engine/session; DATABASE_URL env, default sqlite:///./orbitcare.db
backend/app/models.py          SQLAlchemy models (PLAN §7 tables)
backend/app/engine/config.py   DEFAULT_CONFIG (thresholds + source notes), DEFAULT_WEIGHTS
backend/app/engine/grading.py  division sub-scores + total grade (pure functions, no I/O)
backend/app/pipeline/stages.py 7 stages; backend/app/pipeline/runner.py run_pipeline()
backend/app/api/telemetry.py   /api/telemetry/*   backend/app/api/*.py other routers
backend/tests/                 pytest (test_grading.py golden cases, test_api.py ...)
scripts/generate_sample.py     simulated data generator (seeded, deterministic)
data/sample/workflow_a_31_scenarios.csv
frontend/index.html  frontend/css/theme.css  frontend/js/app.js (hash router)
frontend/js/api.js   frontend/js/pages/<section>.js  frontend/js/engine/grading.js (JS port, later)
frontend/vendor/chart.umd.min.js
docs/  CONTRACT.md ASSUMPTIONS.md TEST_REPORT.md   PROGRESS.md  README.md
```

## 2. Telemetry row (CSV header == JSON keys, exact order)
`timestamp` ISO-8601 UTC, `astronaut_id` str, `mission_day` int>=1, `scenario_id` int 0-31, `scenario_label` str,
`cum_dose_msv` float, `proton_flux_pfu` float, `flare_active` bool(0/1),
`sleep_h` float, `hrv_rmssd_ms` float, `hrv_baseline_ms` float|empty, `fatigue` 0-10, `stress` 0-10,
`loading_index` float, `loading_target` float, `balance_score` 0-100,
`cabin_o2_pct` float, `cabin_co2_ppm` float, `cabin_pressure_kpa` float, `cabin_temp_c` float, `cabin_humidity_pct` float, `scrubber_state` nominal|degraded|offline,
`latency_s` float, `open_medical_flags` int, `source` SIMULATED|USER-ENTERED|LIVE|CACHED|ESTIMATE.
Empty numeric -> null; a division whose required inputs are all null gets score null, status "NO_DATA" and is excluded from the total (weights renormalised).

## 3. Grading engine (backend/app/engine/grading.py) — PLAN §6, illustrative defaults
Every division starts at 100, subtract deductions, clamp 0..100, round 1 dp. Each deduction is a factor `{code,label,value,deduction}`.
- **radiation**: `60*min(cum_dose_msv/600,1)`; `-20` if proton_flux_pfu>=10; `-10` if flare_active.
- **mental_health**: sleep<6 `-15` (sleep<5 `-25` instead); HRV drop% = max(0,(base-hrv)/base*100), deduct `min(30,drop%)` (base = hrv_baseline_ms, else no HRV factor); fatigue `max(0,(f-5)*4)`; stress `max(0,(s-5)*4)`.
- **gravity**: ratio=loading_index/loading_target; if ratio<0.8 deduct `min(40,(0.8-ratio)*100)`; balance<85 deduct `min(30,(85-balance)*0.8)`.
- **life_support**: co2>5000 deduct `min(40,(co2-5000)/50)`; O2 outside [19.5,23.5] deduct `min(30,dist*15)`; pressure outside [97,103] kPa deduct `min(20,dist*4)`; scrubber degraded `-15`, offline `-35`.
- **earth_distance** (computed LAST): tier = 1 if latency_s<2, 2 if <=60, else 3. If any other division status != GREEN: tier2 `-15`, tier3 `-30`. Always: open_medical_flags `-5` each, max `-20`.
- **status(score)**: GREEN >=75, YELLOW 35–74.9, RED <35.
- **grade_letter(score)**: >=95 "A+", >=90 "A", >=75 "B", >=55 "C", >=35 "D", else "F".
- **total**: weighted = Σ w·score (weights radiation .25, life_support .25, mental_health .20, gravity .15, earth_distance .15); `penalty = -10` if count(status in YELLOW,RED) >= 3; `score = weighted + penalty`; **bottleneck**: if any division score <35, `score = min(score, 54.9)` (cannot exceed D), `capped=true`; clamp 0..100, round 1 dp.
- interaction_flags (hypotheses, label "Hypothesis from HRP hazard descriptions"): radiation+mental_health, gravity+mental_health, life_support+mental_health when both non-GREEN.

Signatures:
```python
def status(score: float|None) -> str
def grade_letter(score: float|None) -> str|None
def score_radiation(row: dict, cfg=DEFAULT_CONFIG) -> dict      # DivisionResult
def score_mental_health(row, cfg=...) -> dict
def score_gravity(row, cfg=...) -> dict
def score_life_support(row, cfg=...) -> dict
def score_earth_distance(row, others: dict[str, dict], cfg=...) -> dict
def total_grade(divisions: dict[str, dict], weights=DEFAULT_WEIGHTS) -> dict
def assess(row: dict, cfg=DEFAULT_CONFIG, weights=DEFAULT_WEIGHTS, day1_score: float|None=None) -> dict  # Assessment
```
DivisionResult: `{"key","name","score","grade","status","factors":[...]}`
TotalResult: `{"weighted","penalty","capped","score","grade","status","delta_from_day1"}` (delta = score - (day1_score or 100))
Assessment: `{"astronaut_id","timestamp","mission_day","scenario_id","scenario_label","source","divisions":{key:DivisionResult},"total":TotalResult,"interaction_flags":[{"pair":[a,b],"label"}],"label":"Readiness & Condition Index — Illustrative screening metric, not a medical diagnosis"}`

## 4. API (all JSON; errors `{"detail": str}`)
- `GET /api/health` -> `{"status":"ok","version":"0.1.0"}`
- `POST /api/telemetry/upload` multipart `file` (.csv or .json list/`{"rows":[...]}`) -> IngestResult
- `POST /api/telemetry/ingest` body `{"rows":[TelemetryRow]}` -> IngestResult
- IngestResult: `{"received","accepted","rejected":[{"row":int,"reason":str}],"suspect":[{"row","metric","reason"}],"assessments":[Assessment],"pipeline":[StageReport]}`
- StageReport: `{"stage":1-7,"name","records_in","records_out","rejected","last_run","notes"}`
- `GET /api/telemetry/simulate?astronaut_id=SIM-A1&day=n&scenario_id=k` -> one SIMULATED TelemetryRow (not stored)
- `GET /api/assessments?astronaut_id=` -> `{"items":[Assessment]}` ordered by timestamp (trajectory)
- `GET /api/assessments/latest` -> `{"items":[latest Assessment per astronaut]}`
- `GET /api/pipeline/status` -> `{"stages":[StageReport]}`
- `GET /api/crew` -> `{"items":[{"astronaut_id","name","source":"SIMULATED"}]}`
- `GET /api/alerts` -> `{"items":[{"id","astronaut_id","severity","code","message","created_at","day"}]}`
- `GET /api/spaceweather` (M6) -> `{"status":"LIVE|CACHED|FAILED","fetched_at","age_s","stale":bool,"error":str|null,"data":{...}}`; `POST /api/spaceweather/refresh`
- `DELETE /api/telemetry` -> reset demo data (Settings)
- `GET /api/telemetry?astronaut_id=` -> `{"items":[TelemetryRow + "received_at","suspect":bool]}` ordered by timestamp (raw values for Guard charts)
- `GET /api/settings` / `PUT /api/settings` -> `{"weights":{...},"thresholds":{...},"mission":{"name","start","planned_days"}}`; weights must sum to 1.0 (422 otherwise); new weights apply to later assessments
- `GET /api/reports/assessments.csv?astronaut_id=` -> CSV export; `GET /api/backup` -> JSON dump; `POST /api/restore` -> load dump

## 5. Sample data
31 scenarios = every non-empty subset of the 5 hazards (bitmask 1..31, bit0 radiation, bit1 mental_health, bit2 gravity, bit3 life_support, bit4 earth_distance) plus scenario 0 = Day-1 nominal. Sample CSV: astronaut SIM-A1, day 1 = scenario 0, days 2..32 = scenarios sorted by popcount then value, cumulative dose monotonic, all `source=SIMULATED`, fictional crew only.
`

## File: docs/ASSUMPTIONS.md

`markdown
# ORBITCARE 5X — Assumptions

- The PLAN was supplied as `PLAN.md.docx` and extracted to `PLAN.md` (text).
- Division status: GREEN >= 75; YELLOW 35 to 74.9; RED < 35.
- Letter grade: A+ >= 95; A 90 to 94.9; (further bands per CONTRACT §3).
- Bottleneck cap: if any division score < 35, the total is capped at 54.9 (Grade D maximum).
- Compounding penalty (-10) is applied before the bottleneck cap.
- All deduction coefficients are illustrative defaults (CONTRACT §3), not validated science.
- 31 scenarios = every non-empty subset of the 5 hazards (bitmask 1..31), plus scenario 0 = Day-1 nominal.
- NO_DATA divisions (all required inputs null) are excluded from the total, and the remaining weights are renormalised.
- Hazard interaction flags are hypotheses drawn from HRP hazard descriptions, not validated coefficients.
- Crew, vitals and cabin telemetry are fictional and SIMULATED.
- Local Python on this machine is 3.10.11; the Dockerfile uses Python 3.11.
- Git is not installed on this machine; milestones are checkpointed as zip snapshots in `checkpoints/` until git is available.
- earth_distance "other division flagged" means YELLOW or RED; NO_DATA does not count.
- NO_DATA divisions are excluded from the weighted total, the penalty count and the bottleneck check.
- A single null input skips that factor only; the division is still scored from its other inputs.
- The weighted total is rounded to 1 dp before the penalty and the cap are applied.
- The sample generator uses seed 42 and is fully SIMULATED.

## Sample and ingest assumptions (2026-11-14)

- Sample Day 1 total is 98.5 (A+), not 100, because the 50 mSv starting dose deducts radiation points.
- SIMULATED rows are exempt from the future-timestamp rejection (the sample spans to 2026-12-02). All other sources are rejected when more than 5 minutes in the future.
- Mission start = earliest row when no mission is configured.
- Only the missions, astronauts, health_records, assessments, alerts, and settings tables are implemented so far.
- The 53 suspect flags on the sample are expected, because scenarios change step-wise.
- Any NOAA feed failing fails the whole refresh (no mixed fields).
- The NOAA Kp parser accepts both the legacy array and the new object formats.

## Final M7 assumptions (2026-11-14)

- `CORS_ORIGINS` default is `null,http://localhost:8090,http://127.0.0.1:8090`. The `null` origin is needed for pages opened from `file://` (the single-file build). Remove it for shared deployments.
- Suspect flags are persisted in `health_records.suspect_metrics` as JSON. Rows stored before this change return `null` for that field.
- Settings weights and thresholds apply only to assessments computed after the change. Existing assessments are not recomputed.
- Roadmap hooks (wearables, ECLSS links, predictive ML) are not connected.
- Five of the PLAN §7 tables (`dose_records`, `exercise_sessions`, `balance_tests`, `cabin_telemetry`, `comm_link_log`) are not separate tables. Their values live in `health_records` rows.
`

## File: backend/app/main.py

`python
﻿"""ORBITCARE 5X FastAPI application entry point.

Serves the JSON API under /api and the static frontend at / when the
frontend/ directory exists.
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import db
from .api import assessments, reports, settings, spaceweather, telemetry

APP_VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="ORBITCARE 5X", version=APP_VERSION, lifespan=lifespan)

# "null" is the Origin sent by file:// pages. Local-only default; no wildcard.
DEFAULT_CORS_ORIGINS = "null,http://localhost:8090,http://127.0.0.1:8090"
CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", DEFAULT_CORS_ORIGINS).split(",")
    if o.strip() and o.strip() != "*"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    allow_credentials=False,
)
app.include_router(telemetry.router)
app.include_router(assessments.router)
app.include_router(spaceweather.router)
app.include_router(settings.router)
app.include_router(reports.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": APP_VERSION}


# parents[0]=app, parents[1]=backend, parents[2]=project root
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
`

## File: backend/app/db.py

`python
"""Database engine/session. DATABASE_URL env (default sqlite:///./orbitcare.db)."""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


engine = None
SessionLocal = None


def configure(url: str | None = None):
    """(Re)bind the engine; tests call this with a temp SQLite URL."""
    global engine, SessionLocal
    url = url or os.environ.get("DATABASE_URL", "sqlite:///./orbitcare.db")
    kwargs = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
    if engine is not None:
        engine.dispose()
    engine = create_engine(url, **kwargs)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return engine


def init_db():
    from . import models  # noqa: F401  (register tables)

    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


configure()
`

## File: backend/app/models.py

`python
﻿"""SQLAlchemy 2 models (PLAN section 7 subset used by the pipeline)."""
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
`

## File: backend/app/engine/config.py

`python
﻿"""Engine configuration: thresholds and coefficients with source notes."""
_ILL = "illustrative default"

DEFAULT_CONFIG = {
    "radiation": {
        "career_limit_msv": {"value": 600, "source": "PLAN section 6.1 (career dose ~600 mSv reference); " + _ILL},
        "max_dose_deduction": {"value": 60, "source": _ILL},
        "proton_flux_pfu": {"value": 10, "source": "NOAA S1 solar radiation storm threshold (>=10 pfu)"},
        "proton_deduction": {"value": 20, "source": _ILL},
        "flare_deduction": {"value": 10, "source": _ILL},
    },
    "mental_health": {
        "sleep_low_h": {"value": 6, "source": "PLAN section 6.2; " + _ILL},
        "sleep_low_deduction": {"value": 15, "source": _ILL},
        "sleep_severe_h": {"value": 5, "source": _ILL},
        "sleep_severe_deduction": {"value": 25, "source": _ILL},
        "hrv_max_deduction": {"value": 30, "source": _ILL},
        "fatigue_free": {"value": 5, "source": _ILL},
        "fatigue_coeff": {"value": 4, "source": _ILL},
        "stress_free": {"value": 5, "source": _ILL},
        "stress_coeff": {"value": 4, "source": _ILL},
    },
    "gravity": {
        "loading_ratio_min": {"value": 0.8, "source": "PLAN section 6.2 (80% of target)"},
        "loading_coeff": {"value": 100, "source": _ILL},
        "loading_max_deduction": {"value": 40, "source": _ILL},
        "balance_min": {"value": 85, "source": _ILL},
        "balance_coeff": {"value": 0.8, "source": _ILL},
        "balance_max_deduction": {"value": 30, "source": _ILL},
    },
    "life_support": {
        "co2_ppm_max": {"value": 5000, "source": "PLAN section 6.2 (CO2 > 5,000 ppm); " + _ILL},
        "co2_per_ppm": {"value": 50, "source": _ILL},
        "co2_max_deduction": {"value": 40, "source": _ILL},
        "o2_min_pct": {"value": 19.5, "source": _ILL},
        "o2_max_pct": {"value": 23.5, "source": _ILL},
        "o2_coeff": {"value": 15, "source": _ILL},
        "o2_max_deduction": {"value": 30, "source": _ILL},
        "pressure_min_kpa": {"value": 97, "source": _ILL},
        "pressure_max_kpa": {"value": 103, "source": _ILL},
        "pressure_coeff": {"value": 4, "source": _ILL},
        "pressure_max_deduction": {"value": 20, "source": _ILL},
        "scrubber_degraded_deduction": {"value": 15, "source": _ILL},
        "scrubber_offline_deduction": {"value": 35, "source": _ILL},
    },
    "earth_distance": {
        "tier1_latency_lt_s": {"value": 2, "source": _ILL},
        "tier2_latency_max_s": {"value": 60, "source": _ILL},
        "tier2_deduction": {"value": 15, "source": _ILL},
        "tier3_deduction": {"value": 30, "source": _ILL},
        "flag_deduction": {"value": 5, "source": _ILL},
        "flag_max_deduction": {"value": 20, "source": _ILL},
    },
    "status": {
        "green_min": {"value": 75, "source": "PLAN section 6.3"},
        "yellow_min": {"value": 35, "source": "PLAN section 6.3"},
    },
    "grade": {
        "a_plus_min": {"value": 95, "source": _ILL},
        "a_min": {"value": 90, "source": "PLAN section 6.3"},
        "b_min": {"value": 75, "source": "PLAN section 6.3"},
        "c_min": {"value": 55, "source": "PLAN section 6.3"},
        "d_min": {"value": 35, "source": "PLAN section 6.3"},
    },
    "total": {
        "compound_count": {"value": 3, "source": "PLAN section 6.3"},
        "compound_penalty": {"value": -10, "source": "PLAN section 6.3"},
        "bottleneck_below": {"value": 35, "source": "PLAN section 6.3"},
        "bottleneck_cap": {"value": 54.9, "source": "PLAN section 6.3 (cannot exceed Grade D)"},
    },
}

DEFAULT_WEIGHTS = {
    "radiation": 0.25,
    "life_support": 0.25,
    "mental_health": 0.20,
    "gravity": 0.15,
    "earth_distance": 0.15,
}
`

## File: backend/app/engine/grading.py

`python
﻿"""Grading engine: pure functions, no I/O. Illustrative screening metric, not a diagnosis."""
from .config import DEFAULT_CONFIG, DEFAULT_WEIGHTS

LABEL = "Readiness & Condition Index \u2014 Illustrative screening metric, not a medical diagnosis"
HYPOTHESIS_LABEL = "Hypothesis from HRP hazard descriptions"
NAMES = {
    "radiation": "Radiation",
    "mental_health": "Mental Health",
    "gravity": "Gravity",
    "life_support": "Life Support",
    "earth_distance": "Earth Distance",
}
ORDER = ["radiation", "mental_health", "gravity", "life_support", "earth_distance"]
PAIRS = [("radiation", "mental_health"), ("gravity", "mental_health"), ("life_support", "mental_health")]


def _c(cfg, group, key):
    return cfg[group][key]["value"]


def _num(v):
    if v is None or isinstance(v, bool):
        return None if v is None else float(v)
    if isinstance(v, (int, float)):
        return None if v != v else float(v)
    s = str(v).strip()
    if s == "" or s.lower() in ("nan", "null", "none"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _bool(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    s = str(v).strip().lower()
    if s == "":
        return None
    return s in ("1", "true", "t", "yes", "y", "1.0")


def _r1(x):
    return round(x + 1e-12, 1)


def status(score):
    if score is None:
        return "NO_DATA"
    if score >= 75:
        return "GREEN"
    if score >= 35:
        return "YELLOW"
    return "RED"


def grade_letter(score):
    if score is None:
        return None
    if score >= 95:
        return "A+"
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 55:
        return "C"
    if score >= 35:
        return "D"
    return "F"


def _factor(code, label, value, deduction):
    return {"code": code, "label": label, "value": value, "deduction": round(deduction, 2)}


def _result(key, factors, no_data=False):
    if no_data:
        return {"key": key, "name": NAMES[key], "score": None, "grade": None,
                "status": "NO_DATA", "factors": []}
    score = _r1(max(0.0, min(100.0, 100.0 - sum(f["deduction"] for f in factors))))
    return {"key": key, "name": NAMES[key], "score": score, "grade": grade_letter(score),
            "status": status(score), "factors": factors}


def score_radiation(row, cfg=DEFAULT_CONFIG):
    dose, pf, fl = _num(row.get("cum_dose_msv")), _num(row.get("proton_flux_pfu")), _bool(row.get("flare_active"))
    if dose is None and pf is None and fl is None:
        return _result("radiation", [], True)
    f = []
    if dose is not None:
        d = _c(cfg, "radiation", "max_dose_deduction") * min(dose / _c(cfg, "radiation", "career_limit_msv"), 1)
        if d > 0:
            f.append(_factor("CUM_DOSE", "Cumulative dose vs career limit", dose, d))
    if pf is not None and pf >= _c(cfg, "radiation", "proton_flux_pfu"):
        f.append(_factor("PROTON_FLUX", "Proton flux >= threshold", pf, _c(cfg, "radiation", "proton_deduction")))
    if fl:
        f.append(_factor("FLARE_ACTIVE", "Solar flare active", 1, _c(cfg, "radiation", "flare_deduction")))
    return _result("radiation", f)


def score_mental_health(row, cfg=DEFAULT_CONFIG):
    sl, hrv, base = _num(row.get("sleep_h")), _num(row.get("hrv_rmssd_ms")), _num(row.get("hrv_baseline_ms"))
    fa, st = _num(row.get("fatigue")), _num(row.get("stress"))
    if sl is None and hrv is None and fa is None and st is None:
        return _result("mental_health", [], True)
    g = lambda k: _c(cfg, "mental_health", k)
    f = []
    if sl is not None:
        if sl < g("sleep_severe_h"):
            f.append(_factor("SLEEP_SEVERE", "Sleep below severe threshold", sl, g("sleep_severe_deduction")))
        elif sl < g("sleep_low_h"):
            f.append(_factor("SLEEP_LOW", "Sleep below 6 h", sl, g("sleep_low_deduction")))
    if hrv is not None and base is not None and base > 0:
        drop = max(0.0, (base - hrv) / base * 100)
        if drop > 0:
            f.append(_factor("HRV_DROP", "HRV RMSSD drop vs baseline (%)", round(drop, 2), min(g("hrv_max_deduction"), drop)))
    if fa is not None and fa > g("fatigue_free"):
        f.append(_factor("FATIGUE", "Fatigue above 5", fa, (fa - g("fatigue_free")) * g("fatigue_coeff")))
    if st is not None and st > g("stress_free"):
        f.append(_factor("STRESS", "Stress above 5", st, (st - g("stress_free")) * g("stress_coeff")))
    return _result("mental_health", f)


def score_gravity(row, cfg=DEFAULT_CONFIG):
    li, lt, bal = _num(row.get("loading_index")), _num(row.get("loading_target")), _num(row.get("balance_score"))
    ratio = li / lt if (li is not None and lt) else None
    if ratio is None and bal is None:
        return _result("gravity", [], True)
    g = lambda k: _c(cfg, "gravity", k)
    f = []
    if ratio is not None and ratio < g("loading_ratio_min"):
        f.append(_factor("LOADING_LOW", "Resistive loading below 80% of target (ratio)", round(ratio, 3),
                         min(g("loading_max_deduction"), (g("loading_ratio_min") - ratio) * g("loading_coeff"))))
    if bal is not None and bal < g("balance_min"):
        f.append(_factor("BALANCE_LOW", "Vestibular balance score low", bal,
                         min(g("balance_max_deduction"), (g("balance_min") - bal) * g("balance_coeff"))))
    return _result("gravity", f)


def score_life_support(row, cfg=DEFAULT_CONFIG):
    o2, co2, p = _num(row.get("cabin_o2_pct")), _num(row.get("cabin_co2_ppm")), _num(row.get("cabin_pressure_kpa"))
    sc = row.get("scrubber_state")
    sc = str(sc).strip().lower() if sc is not None and str(sc).strip() != "" else None
    if o2 is None and co2 is None and p is None and sc is None:
        return _result("life_support", [], True)
    g = lambda k: _c(cfg, "life_support", k)
    f = []
    if co2 is not None and co2 > g("co2_ppm_max"):
        f.append(_factor("CO2_HIGH", "Cabin CO2 above 5000 ppm", co2, min(g("co2_max_deduction"), (co2 - g("co2_ppm_max")) / g("co2_per_ppm"))))
    if o2 is not None and (o2 < g("o2_min_pct") or o2 > g("o2_max_pct")):
        dist = g("o2_min_pct") - o2 if o2 < g("o2_min_pct") else o2 - g("o2_max_pct")
        f.append(_factor("O2_OUT_OF_RANGE", "Cabin O2 outside 19.5-23.5 %", o2, min(g("o2_max_deduction"), dist * g("o2_coeff"))))
    if p is not None and (p < g("pressure_min_kpa") or p > g("pressure_max_kpa")):
        dist = g("pressure_min_kpa") - p if p < g("pressure_min_kpa") else p - g("pressure_max_kpa")
        f.append(_factor("PRESSURE_OUT_OF_RANGE", "Cabin pressure outside 97-103 kPa", p, min(g("pressure_max_deduction"), dist * g("pressure_coeff"))))
    if sc == "degraded":
        f.append(_factor("SCRUBBER_DEGRADED", "CO2 scrubber degraded", sc, g("scrubber_degraded_deduction")))
    elif sc == "offline":
        f.append(_factor("SCRUBBER_OFFLINE", "CO2 scrubber offline", sc, g("scrubber_offline_deduction")))
    return _result("life_support", f)


def score_earth_distance(row, others, cfg=DEFAULT_CONFIG):
    lat, flags = _num(row.get("latency_s")), _num(row.get("open_medical_flags"))
    if lat is None and flags is None:
        return _result("earth_distance", [], True)
    g = lambda k: _c(cfg, "earth_distance", k)
    f = []
    if lat is not None:
        tier = 1 if lat < g("tier1_latency_lt_s") else (2 if lat <= g("tier2_latency_max_s") else 3)
        any_bad = any((o or {}).get("status") in ("YELLOW", "RED") for o in (others or {}).values())
        if tier >= 2 and any_bad:
            f.append(_factor("LATENCY_TIER%d" % tier, "Comms latency tier %d while another division is not GREEN" % tier,
                             lat, g("tier2_deduction") if tier == 2 else g("tier3_deduction")))
    if flags is not None and flags > 0:
        f.append(_factor("OPEN_MEDICAL_FLAGS", "Open medical flags", int(flags),
                         min(g("flag_max_deduction"), flags * g("flag_deduction"))))
    return _result("earth_distance", f)


def total_grade(divisions, weights=DEFAULT_WEIGHTS, cfg=DEFAULT_CONFIG, day1_score=None):
    scored = {k: d for k, d in divisions.items() if d.get("score") is not None}
    wsum = sum(weights.get(k, 0) for k in scored)
    if not scored or wsum <= 0:
        return {"weighted": None, "penalty": 0, "capped": False, "score": None, "grade": None,
                "status": "NO_DATA", "delta_from_day1": None}
    weighted = sum(weights.get(k, 0) * d["score"] for k, d in scored.items()) / wsum
    t = lambda k: _c(cfg, "total", k)
    n_bad = sum(1 for d in scored.values() if d["status"] in ("YELLOW", "RED"))
    penalty = t("compound_penalty") if n_bad >= t("compound_count") else 0
    score = weighted + penalty
    capped = False
    if any(d["score"] < t("bottleneck_below") for d in scored.values()):
        capped = True
        score = min(score, t("bottleneck_cap"))
    score = _r1(max(0.0, min(100.0, score)))
    base = 100.0 if day1_score is None else day1_score
    return {"weighted": _r1(weighted), "penalty": penalty, "capped": capped, "score": score,
            "grade": grade_letter(score), "status": status(score), "delta_from_day1": round(score - base, 1)}


def assess(row, cfg=DEFAULT_CONFIG, weights=DEFAULT_WEIGHTS, day1_score=None):
    divs = {
        "radiation": score_radiation(row, cfg),
        "mental_health": score_mental_health(row, cfg),
        "gravity": score_gravity(row, cfg),
        "life_support": score_life_support(row, cfg),
    }
    divs["earth_distance"] = score_earth_distance(row, dict(divs), cfg)
    divs = {k: divs[k] for k in ORDER}
    total = total_grade(divs, weights, cfg, day1_score)
    flags = [{"pair": [a, b], "label": HYPOTHESIS_LABEL} for a, b in PAIRS
             if divs[a]["status"] in ("YELLOW", "RED") and divs[b]["status"] in ("YELLOW", "RED")]
    md = _num(row.get("mission_day")); sid = _num(row.get("scenario_id"))
    return {"astronaut_id": row.get("astronaut_id"), "timestamp": row.get("timestamp"),
            "mission_day": None if md is None else int(md),
            "scenario_id": None if sid is None else int(sid),
            "scenario_label": row.get("scenario_label"), "source": row.get("source"),
            "divisions": divs, "total": total, "interaction_flags": flags, "label": LABEL}
`

## File: backend/app/pipeline/runner.py

`python
﻿"""run_pipeline(): executes the 7 stages and keeps the latest StageReports in memory."""
import functools
import threading

from ..models import ensure_suspect_column
from . import stages as st

_lock = threading.Lock()
_run_lock = threading.RLock()
LATEST = {i: st.empty_report(i) for i in range(1, 8)}
LATEST_HUD: dict = {}


def reset_reports():
    with _lock:
        for i in range(1, 8):
            LATEST[i] = st.empty_report(i)
        LATEST_HUD.clear()


def status_reports():
    with _lock:
        return [dict(LATEST[i]) for i in range(1, 8)]


def run_pipeline(session, rows, default_source="USER-ENTERED"):
    """Run all stages over raw row dicts; commits on success. Returns IngestResult."""
    from ..api.settings import effective  # persisted thresholds/weights (M7)
    cfg, weights, _ = effective(session)
    ensure_suspect_column(session)
    ctx = st.Ctx(session=session, raw=list(rows), default_source=default_source)
    reports = []
    with _run_lock:
        orig = st.assess
        st.assess = functools.partial(orig, cfg=cfg, weights=weights)
        try:
            for fn in (st.stage1_ingest, st.stage2_validate, st.stage3_baseline, st.stage4_triage,
                       st.stage5_grade, st.stage6_hud, st.stage7_alerts):
                reports.append(fn(ctx))
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            st.assess = orig
    with _lock:
        for r in reports:
            LATEST[r["stage"]] = r
        LATEST_HUD.update(ctx.hud)
    return {"received": len(ctx.raw), "accepted": len(ctx.items), "rejected": ctx.rejected,
            "suspect": ctx.suspect, "assessments": ctx.assessments, "pipeline": reports}
`

## File: backend/app/pipeline/stages.py

`python
﻿"""The 7 pipeline stages (PLAN 6.4). Each takes a Ctx, mutates it, returns a StageReport."""
import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from ..engine.grading import assess
from ..models import AlertRecord, Astronaut, AssessmentRecord, HealthRecord, Mission

COLUMNS = [
    "timestamp", "astronaut_id", "mission_day", "scenario_id", "scenario_label",
    "cum_dose_msv", "proton_flux_pfu", "flare_active", "sleep_h", "hrv_rmssd_ms",
    "hrv_baseline_ms", "fatigue", "stress", "loading_index", "loading_target",
    "balance_score", "cabin_o2_pct", "cabin_co2_ppm", "cabin_pressure_kpa",
    "cabin_temp_c", "cabin_humidity_pct", "scrubber_state", "latency_s",
    "open_medical_flags", "source",
]
INT_FIELDS = {"mission_day", "scenario_id", "open_medical_flags"}
FLOAT_FIELDS = {
    "cum_dose_msv", "proton_flux_pfu", "sleep_h", "hrv_rmssd_ms", "hrv_baseline_ms", "fatigue",
    "stress", "loading_index", "loading_target", "balance_score", "cabin_o2_pct",
    "cabin_co2_ppm", "cabin_pressure_kpa", "cabin_temp_c", "cabin_humidity_pct", "latency_s",
}
RANGES = {  # inclusive (lo, hi); None = unbounded
    "mission_day": (1, None), "scenario_id": (0, 31), "open_medical_flags": (0, None),
    "cum_dose_msv": (0, None), "proton_flux_pfu": (0, None), "sleep_h": (0, 24),
    "hrv_rmssd_ms": (0, 500), "hrv_baseline_ms": (0, 500), "fatigue": (0, 10), "stress": (0, 10),
    "loading_index": (0, None), "loading_target": (0, None), "balance_score": (0, 100),
    "cabin_o2_pct": (0, 100), "cabin_co2_ppm": (0, 100000), "cabin_pressure_kpa": (0, 1000),
    "cabin_temp_c": (-50, 100), "cabin_humidity_pct": (0, 100), "latency_s": (0, None),
}
SCRUBBER = {"nominal", "degraded", "offline"}
SOURCES = {"SIMULATED", "USER-ENTERED", "LIVE", "CACHED", "ESTIMATE"}
DEFAULT_MISSION_START = "2026-11-01T00:00:00Z"
FUTURE_TOLERANCE = timedelta(minutes=5)
WINDOW = timedelta(days=14)
ESTABLISH_DAYS = 7
SPIKE_METRICS = ["hrv_rmssd_ms", "sleep_h", "fatigue", "stress", "cabin_co2_ppm",
                 "cabin_o2_pct", "cabin_pressure_kpa", "loading_index", "balance_score"]
BASELINE_METRICS = ["hrv_rmssd_ms", "sleep_h", "fatigue", "stress"]
STAGE_NAMES = ["Bio-Sensors", "Validation", "Processing", "AI Triage",
               "5X Guards & Grading", "Med-HUD", "Protocols"]


def now_utc():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_ts(v):
    if isinstance(v, datetime):
        dt = v
    else:
        s = str(v).strip()
        if s.endswith(("Z", "z")):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass
class Ctx:
    session: object
    raw: list
    default_source: str = "USER-ENTERED"
    items: list = field(default_factory=list)       # accepted items (chronological after stage 2)
    all_items: list = field(default_factory=list)
    rejected: list = field(default_factory=list)
    suspect: list = field(default_factory=list)
    series: dict = field(default_factory=dict)      # astronaut -> list of (dt, row) sorted
    assessments: list = field(default_factory=list)
    hud: dict = field(default_factory=dict)
    alerts_created: list = field(default_factory=list)
    anomalies: list = field(default_factory=list)
    received_at: datetime = field(default_factory=now_utc)


def report(stage, rin, rout, rejected, notes):
    return {"stage": stage, "name": STAGE_NAMES[stage - 1], "records_in": rin,
            "records_out": rout, "rejected": rejected, "last_run": iso(now_utc()), "notes": notes}


def empty_report(stage):
    r = report(stage, 0, 0, 0, "No data processed yet")
    r["last_run"] = None
    return r


# ---------- helpers ----------
def mad(vals, med=None):
    med = statistics.median(vals) if med is None else med
    return statistics.median([abs(v - med) for v in vals])


def mad_floor(m, med):
    return max(m, 0.02 * abs(med), 1e-6)


def prior_window(ctx, astro, ts):
    return [r for dt, r in ctx.series.get(astro, []) if dt < ts and ts - dt <= WINDOW]


def _values(rows, metric):
    return [r[metric] for r in rows if r.get(metric) is not None]


# ---------- stage 1 ----------
def stage1_ingest(ctx):
    counts = {}
    for i, raw in enumerate(ctx.raw, start=1):
        item = {"idx": i, "raw": raw if isinstance(raw, dict) else {}, "row": None,
                "suspect": [], "anomalies": [], "received_at": ctx.received_at}
        src = str(item["raw"].get("source") or "").strip().upper() or ctx.default_source
        item["source"] = src
        counts[src] = counts.get(src, 0) + 1
        item["is_dict"] = isinstance(raw, dict)
        ctx.all_items.append(item)
    notes = "received per source: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
    return report(1, len(ctx.raw), len(ctx.all_items), 0, notes or "no records")


# ---------- stage 2 ----------
def _coerce(raw, source):
    row = {}
    for c in COLUMNS:
        v = raw.get(c)
        if isinstance(v, str):
            v = v.strip()
        row[c] = None if v is None or v == "" else v
    row["source"] = source
    if source not in SOURCES:
        return None, f"invalid source '{source}'"
    if not row["astronaut_id"]:
        return None, "missing astronaut_id"
    row["astronaut_id"] = str(row["astronaut_id"])
    if row["timestamp"] is None:
        return None, "missing timestamp"
    try:
        dt = parse_ts(row["timestamp"])
    except (ValueError, TypeError):
        return None, f"invalid timestamp '{row['timestamp']}'"
    row["timestamp"] = iso(dt)
    for f in INT_FIELDS | FLOAT_FIELDS:
        v = row[f]
        if v is None:
            continue
        try:
            num = float(v)
            if math.isnan(num) or math.isinf(num):
                raise ValueError
            if f in INT_FIELDS:
                if num != int(num):
                    raise ValueError
                num = int(num)
        except (ValueError, TypeError):
            return None, f"invalid value for {f}: '{v}'"
        lo, hi = RANGES.get(f, (None, None))
        if (lo is not None and num < lo) or (hi is not None and num > hi):
            return None, f"{f} out of range: {num}"
        row[f] = num
    if row["mission_day"] is None:
        return None, "missing mission_day"
    fa = row["flare_active"]
    if fa is not None:
        s = str(fa).strip().lower()
        if s in ("1", "true", "yes", "1.0"):
            row["flare_active"] = 1
        elif s in ("0", "false", "no", "0.0"):
            row["flare_active"] = 0
        else:
            return None, f"invalid value for flare_active: '{fa}'"
    sc = row["scrubber_state"]
    if sc is not None:
        sc = str(sc).lower()
        if sc not in SCRUBBER:
            return None, f"invalid scrubber_state '{sc}'"
        row["scrubber_state"] = sc
    return row, dt


def stage2_validate(ctx):
    s = ctx.session
    stored = s.execute(select(HealthRecord).order_by(HealthRecord.timestamp)).scalars().all()
    seen = set()
    for r in stored:
        seen.add((r.astronaut_id, r.timestamp))
        row = {c: getattr(r, c) for c in COLUMNS}
        ctx.series.setdefault(r.astronaut_id, []).append((parse_ts(r.timestamp), row))
    mission = s.execute(select(Mission).order_by(Mission.id)).scalars().first()
    now = now_utc()

    parsed = []
    for item in ctx.all_items:
        if not item["is_dict"]:
            ctx.rejected.append({"row": item["idx"], "reason": "row is not an object"})
            continue
        row, dt = _coerce(item["raw"], item["source"])
        if row is None:
            ctx.rejected.append({"row": item["idx"], "reason": dt})
            continue
        item["row"], item["dt"] = row, dt
        parsed.append(item)

    if mission:
        start = parse_ts(mission.start)
    elif parsed or stored:
        cands = [i["dt"] for i in parsed] + [dt for rows in ctx.series.values() for dt, _ in rows]
        start = min(cands)  # no mission configured: earliest row defines the start
    else:
        start = parse_ts(DEFAULT_MISSION_START)

    parsed.sort(key=lambda i: (i["dt"], i["idx"]))
    for item in parsed:
        row, dt = item["row"], item["dt"]
        key = (row["astronaut_id"], row["timestamp"])
        # SIMULATED mission-time rows are exempt from the future check (sample spans mission days ahead).
        if row["source"] != "SIMULATED" and dt > now + FUTURE_TOLERANCE:
            ctx.rejected.append({"row": item["idx"], "reason": "timestamp in the future (>5 min)"})
            continue
        if dt < start:
            ctx.rejected.append({"row": item["idx"], "reason": f"timestamp before mission start {iso(start)}"})
            continue
        if key in seen:
            ctx.rejected.append({"row": item["idx"], "reason": "duplicate astronaut_id+timestamp"})
            continue
        seen.add(key)
        prior = prior_window(ctx, row["astronaut_id"], dt)
        for m in SPIKE_METRICS:
            vals = _values(prior, m)
            if row[m] is None or len(vals) < ESTABLISH_DAYS:
                continue
            med = statistics.median(vals)
            md = mad_floor(mad(vals, med), med)
            if abs(row[m] - med) > 5 * md:
                reason = f"{row[m]} deviates >5 MAD from rolling median {round(med, 2)}"
                item["suspect"].append({"row": item["idx"], "metric": m, "reason": reason})
        ctx.suspect.extend(item["suspect"])
        ctx.items.append(item)
        ctx.series.setdefault(row["astronaut_id"], []).append((dt, row))
    for rows in ctx.series.values():
        rows.sort(key=lambda t: t[0])
    ctx.rejected.sort(key=lambda r: r["row"])
    notes = (f"accepted {len(ctx.items)}, rejected {len(ctx.rejected)}, "
             f"suspect {len(ctx.suspect)} (spikes >5 MAD)")
    return report(2, len(ctx.all_items), len(ctx.items), len(ctx.rejected), notes)


# ---------- stage 3 ----------
def stage3_baseline(ctx):
    established = 0
    for item in ctx.items:
        row, dt = item["row"], item["dt"]
        prior = prior_window(ctx, row["astronaut_id"], dt)
        days = {r["timestamp"][:10] for r in prior}
        ok = len(days) >= ESTABLISH_DAYS
        base = {}
        if ok:
            for m in BASELINE_METRICS:
                vals = _values(prior, m)
                if len(vals) >= 3:
                    med = statistics.median(vals)
                    base[m] = {"median": round(med, 3), "mad": round(mad(vals, med), 3), "n": len(vals)}
            if row["hrv_baseline_ms"] is None and "hrv_rmssd_ms" in base:
                row["hrv_baseline_ms"] = base["hrv_rmssd_ms"]["median"]
        item["baseline"] = {"established": ok, "days": len(days), "metrics": base}
        established += ok
    notes = (f"baseline established for {established}/{len(ctx.items)} records "
             f"(rolling 14-day median/MAD, after {ESTABLISH_DAYS} days)")
    return report(3, len(ctx.items), len(ctx.items), 0, notes)


# ---------- stage 4 ----------
def stage4_triage(ctx):
    for item in ctx.items:
        row, dt, b = item["row"], item["dt"], item["baseline"]
        if not b["established"]:
            continue
        prior = prior_window(ctx, row["astronaut_id"], dt)
        for m, st in b["metrics"].items():
            x = row.get(m)
            if x is None:
                continue
            vals = _values(prior, m)
            med = st["median"]
            sd = 1.4826 * mad_floor(st["mad"], med)
            z = (x - med) / sd
            found = None
            if abs(z) >= 3:
                found = {"kind": "robust_z", "z": round(z, 2)}
            else:
                ew = vals[0] if vals else x
                for v in vals[1:] + [x]:
                    ew = 0.3 * v + 0.7 * ew
                dz = (ew - med) / sd
                recent = vals[-2:] + [x]
                if len(recent) == 3 and all(abs((v - med) / sd) >= 2 for v in recent) \
                        and all((v - med) * (x - med) > 0 for v in recent):
                    found = {"kind": "sustained_shift", "z": round(z, 2)}
                elif abs(dz) >= 2:
                    found = {"kind": "ewma_drift", "z": round(dz, 2)}
            if found:
                a = {"row": item["idx"], "astronaut_id": row["astronaut_id"], "metric": m,
                     "value": x, "baseline_median": med, **found}
                item["anomalies"].append(a)
                ctx.anomalies.append(a)
    notes = f"{len(ctx.anomalies)} anomalies (robust z>=3, EWMA drift, sustained shift)"
    return report(4, len(ctx.items), len(ctx.items), 0, notes)


# ---------- stage 5 ----------
def stage5_grade(ctx):
    s = ctx.session
    day1 = {}
    known = set()
    for aid in {i["row"]["astronaut_id"] for i in ctx.items}:
        first = s.execute(select(AssessmentRecord).where(AssessmentRecord.astronaut_id == aid)
                          .order_by(AssessmentRecord.timestamp).limit(1)).scalars().first()
        if first is not None and first.total_score is not None:
            day1[aid] = first.total_score
    for item in ctx.items:
        row = item["row"]
        aid = row["astronaut_id"]
        a = assess(row, day1_score=day1.get(aid))
        if aid not in day1 and a["total"]["score"] is not None:
            day1[aid] = a["total"]["score"]
        ctx.assessments.append(a)
        item["assessment"] = a
        s.add(HealthRecord(**{c: row[c] for c in COLUMNS}, received_at=item["received_at"],
                          suspect_metrics=[{"metric": x["metric"], "reason": x["reason"]} for x in item["suspect"]]))
        s.add(AssessmentRecord(astronaut_id=aid, timestamp=row["timestamp"],
                               mission_day=row["mission_day"], total_score=a["total"]["score"],
                               grade=a["total"]["grade"], payload=a))
        if aid not in known and s.get(Astronaut, aid) is None:
            s.add(Astronaut(astronaut_id=aid, name=f"Crew {aid}", source="SIMULATED"))
        known.add(aid)
    s.flush()
    capped = sum(1 for a in ctx.assessments if a["total"]["capped"])
    return report(5, len(ctx.items), len(ctx.assessments), 0,
                  f"{len(ctx.assessments)} assessments; {capped} bottleneck-capped")


# ---------- stage 6 ----------
def stage6_hud(ctx):
    s = ctx.session
    aids = sorted({a["astronaut_id"] for a in ctx.assessments})
    for aid in aids:
        recs = s.execute(select(AssessmentRecord).where(AssessmentRecord.astronaut_id == aid)
                         .order_by(AssessmentRecord.timestamp)).scalars().all()
        if not recs:
            continue
        latest = recs[-1].payload
        ctx.hud[aid] = {
            "astronaut_id": aid, "generated_at": iso(now_utc()), "latest": latest,
            "divisions": {k: {"score": d["score"], "grade": d["grade"], "status": d["status"]}
                          for k, d in latest["divisions"].items()},
            "total": latest["total"],
            "trajectory": [{"mission_day": r.mission_day, "timestamp": r.timestamp,
                            "score": r.total_score, "grade": r.grade} for r in recs],
        }
    return report(6, len(ctx.assessments), len(ctx.hud), 0,
                  f"HUD payload built for {len(ctx.hud)} astronaut(s); payload age 0 s")


# ---------- stage 7 ----------
def stage7_alerts(ctx):
    s = ctx.session
    existing = {(a.astronaut_id, a.code, a.day) for a in s.execute(select(AlertRecord)).scalars()}
    created = 0
    for a in ctx.assessments:
        aid, day = a["astronaut_id"], a["mission_day"]
        cands = []
        for k, d in a["divisions"].items():
            if d["status"] == "RED":
                cands.append((f"DIV_{k.upper()}_RED", "critical", f"{d['name']} is RED (score {d['score']})"))
            elif d["status"] == "YELLOW":
                cands.append((f"DIV_{k.upper()}_YELLOW", "warning", f"{d['name']} is YELLOW (score {d['score']})"))
        if a["total"]["capped"]:
            cands.append(("BOTTLENECK_CAP", "critical",
                          f"Total grade capped at D by critical division (score {a['total']['score']})"))
        for code, sev, msg in cands:
            key = (aid, code, day)
            if key in existing:
                continue
            existing.add(key)
            rec = AlertRecord(astronaut_id=aid, severity=sev, code=code, message=msg, day=day)
            s.add(rec)
            ctx.alerts_created.append(code)
            created += 1
    s.flush()
    return report(7, len(ctx.assessments), created, 0, f"{created} alert(s) created (de-duplicated per astronaut/code/day)")
`

## File: backend/app/services/noaa.py

`python
﻿"""NOAA SWPC live space-weather client with in-memory cache.

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
`

## File: backend/app/api/telemetry.py

`python
﻿"""/api/telemetry/* endpoints."""
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
`

## File: backend/app/api/assessments.py

`python
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
`

## File: backend/app/api/settings.py

`python
﻿"""/api/settings, POST /api/simulate/assess. Settings persist in the settings table."""
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
`

## File: backend/app/api/spaceweather.py

`python
﻿"""/api/spaceweather endpoints (NOAA SWPC, cached polling)."""
from fastapi import APIRouter

from ..services import noaa

router = APIRouter(prefix="/api/spaceweather", tags=["spaceweather"])


@router.get("")
async def get_spaceweather() -> dict:
    return await noaa.get_spaceweather()


@router.post("/refresh")
async def refresh_spaceweather() -> dict:
    return await noaa.get_spaceweather(force=True)
`

## File: backend/app/api/reports.py

`python
﻿"""/api/reports/assessments.csv, /api/backup, /api/restore."""
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
`

## File: scripts/generate_sample.py

`python
#!/usr/bin/env python3
"""ORBITCARE 5X simulated Workflow A telemetry generator.

Every value is SIMULATED for a fictional crew member. Stdlib only, seeded
(SEED=42), deterministic. Writes the CSV and a JSON twin with identical rows,
columns in CONTRACT section 2 order.

Usage:
    python scripts/generate_sample.py [--astronaut SIM-A1] [--out PATH]
"""
import argparse
import csv
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

SEED = 42
MISSION_START = datetime(2026, 11, 1, tzinfo=timezone.utc)
BASE_DOSE_MSV = 50.0
DOSE_PER_DAY_MSV = 0.5
DOSE_PER_RADIATION_DAY_MSV = 2.0
SOURCE = "SIMULATED"

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data" / "sample" / "workflow_a_31_scenarios.csv"

# bit value, hazard key, short label. bit0 radiation ... bit4 earth_distance.
HAZARD_BITS = [
    (1, "radiation", "RAD"),
    (2, "mental_health", "MH"),
    (4, "gravity", "GRAV"),
    (8, "life_support", "LS"),
    (16, "earth_distance", "EARTH"),
]

COLUMNS = [
    "timestamp",
    "astronaut_id",
    "mission_day",
    "scenario_id",
    "scenario_label",
    "cum_dose_msv",
    "proton_flux_pfu",
    "flare_active",
    "sleep_h",
    "hrv_rmssd_ms",
    "hrv_baseline_ms",
    "fatigue",
    "stress",
    "loading_index",
    "loading_target",
    "balance_score",
    "cabin_o2_pct",
    "cabin_co2_ppm",
    "cabin_pressure_kpa",
    "cabin_temp_c",
    "cabin_humidity_pct",
    "scrubber_state",
    "latency_s",
    "open_medical_flags",
    "source",
]

rng = random.Random(SEED)


def _jitter(value, spread, ndigits):
    """Seeded uniform jitter around a nominal value."""
    return round(value + rng.uniform(-spread, spread), ndigits)


def active_hazards(scenario_id):
    return {key for bit, key, _ in HAZARD_BITS if scenario_id & bit}


def scenario_label(scenario_id):
    if scenario_id == 0:
        return "NOMINAL"
    return "+".join(lbl for bit, _, lbl in HAZARD_BITS if scenario_id & bit)


def scenario_sequence():
    """Day 1 = scenario 0; days 2..32 = scenarios 1..31 by popcount, then value."""
    subsets = sorted(range(1, 32), key=lambda v: (bin(v).count("1"), v))
    return [0] + subsets


def make_row(astronaut_id, day, scenario_id, cum_dose):
    """One CONTRACT section 2 telemetry row as a dict (exact column order)."""
    hz = active_hazards(scenario_id)
    timestamp = (MISSION_START + timedelta(days=day - 1)).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Nominal values with small seeded jitter (always drawn, so the stream is stable).
    proton = max(0.0, _jitter(0.5, 0.1, 2))
    flare = 0
    sleep = _jitter(7.5, 0.2, 2)
    hrv = _jitter(55.0, 1.5, 1)
    hrv_baseline = 55.0
    fatigue = _jitter(2.0, 0.3, 1)
    stress = _jitter(2.0, 0.3, 1)
    loading = _jitter(100.0, 1.0, 1)
    loading_target = 100.0
    balance = _jitter(95.0, 1.0, 1)
    o2 = _jitter(21.0, 0.1, 2)
    co2 = float(round(_jitter(2500.0, 50.0, 0)))
    pressure = _jitter(101.3, 0.2, 2)
    temp = _jitter(22.0, 0.3, 1)
    humidity = _jitter(45.0, 1.0, 1)
    scrubber = "nominal"
    latency = max(0.0, _jitter(1.3, 0.05, 2))
    flags = 0

    # Hazard degradation (exact values, no jitter).
    if "radiation" in hz:
        proton, flare = 15.0, 1
    if "mental_health" in hz:
        sleep, hrv, fatigue, stress = 4.8, 35.0, 8.0, 8.0
    if "gravity" in hz:
        loading, balance = 55.0, 70.0
    if "life_support" in hz:
        co2, o2, scrubber = 6500.0, 19.0, "degraded"
    if "earth_distance" in hz:
        latency, flags = 1200.0, 2

    return {
        "timestamp": timestamp,
        "astronaut_id": astronaut_id,
        "mission_day": day,
        "scenario_id": scenario_id,
        "scenario_label": scenario_label(scenario_id),
        "cum_dose_msv": float(cum_dose),
        "proton_flux_pfu": float(proton),
        "flare_active": flare,
        "sleep_h": float(sleep),
        "hrv_rmssd_ms": float(hrv),
        "hrv_baseline_ms": float(hrv_baseline),
        "fatigue": float(fatigue),
        "stress": float(stress),
        "loading_index": float(loading),
        "loading_target": float(loading_target),
        "balance_score": float(balance),
        "cabin_o2_pct": float(o2),
        "cabin_co2_ppm": float(co2),
        "cabin_pressure_kpa": float(pressure),
        "cabin_temp_c": float(temp),
        "cabin_humidity_pct": float(humidity),
        "scrubber_state": scrubber,
        "latency_s": float(latency),
        "open_medical_flags": flags,
        "source": SOURCE,
    }


def build_rows(astronaut_id):
    rng.seed(SEED)  # deterministic on every call
    rows = []
    cum = BASE_DOSE_MSV
    for day, scenario_id in enumerate(scenario_sequence(), start=1):
        if day > 1:
            # Dose accrues daily; radiation days add extra dose. Monotonic.
            cum += DOSE_PER_DAY_MSV
            if scenario_id & 1:
                cum += DOSE_PER_RADIATION_DAY_MSV
        rows.append(make_row(astronaut_id, day, scenario_id, round(cum, 2)))
    return rows


def write_outputs(rows, csv_path):
    csv_path = Path(csv_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: ("" if row[k] is None else row[k]) for k in COLUMNS})

    json_path = csv_path.with_suffix(".json")
    with json_path.open("w", encoding="utf-8") as f:
        json.dump({"rows": rows}, f, indent=2)
        f.write("\n")
    return csv_path, json_path


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate SIMULATED ORBITCARE 5X Workflow A sample (32 days)."
    )
    parser.add_argument("--astronaut", default="SIM-A1", help="fictional crew id")
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help="CSV output path; a .json twin is written beside it",
    )
    args = parser.parse_args(argv)

    rows = build_rows(args.astronaut)
    csv_path, json_path = write_outputs(rows, args.out)
    print(f"wrote {len(rows)} rows -> {csv_path}")
    print(f"wrote {len(rows)} rows -> {json_path}")


if __name__ == "__main__":
    main()
`

## File: scripts/make_test_uploads.py

`python
"""Generate SIMULATED test upload files, one per hazard mix, into data/test_uploads/.

Each file uses its own fictional astronaut ID so files can be uploaded one after
another without being rejected as duplicates. Day 1 is nominal; days 2-8 have the
chosen hazards switched on, so the grade visibly drops after Day 1.
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_sample as g  # noqa: E402

OUT = g.ROOT / "data" / "test_uploads"
DAYS = 8

# (file name, astronaut id, scenario bitmask) - bits: 1 RAD, 2 MH, 4 GRAV, 8 LS, 16 ED
FILES = [
    ("01_radiation_only", "SIM-RAD", 1),
    ("02_mental_health_only", "SIM-MH", 2),
    ("03_gravity_only", "SIM-GRAV", 4),
    ("04_life_support_only", "SIM-LS", 8),
    ("05_earth_distance_only", "SIM-ED", 16),
    ("06_radiation_plus_mental_health", "SIM-RAD-MH", 3),
    ("07_life_support_plus_mental_health", "SIM-LS-MH", 10),
    ("08_gravity_plus_mental_health", "SIM-GRAV-MH", 6),
    ("09_three_hazards_grav_ls_mh", "SIM-3HAZ", 14),
    ("10_all_five_hazards", "SIM-ALL5", 31),
]


def rows_for(astronaut_id, scenario_id):
    rows, dose = [], g.BASE_DOSE_MSV
    for day in range(1, DAYS + 1):
        sid = 0 if day == 1 else scenario_id
        if day > 1:
            dose += g.DOSE_PER_DAY_MSV + (g.DOSE_PER_RADIATION_DAY_MSV if sid & 1 else 0)
        rows.append(g.make_row(astronaut_id, day, sid, round(dose, 2)))
    return rows


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=g.COLUMNS)
        w.writeheader()
        w.writerows(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, astro, sid in FILES:
        write_csv(OUT / f"{name}.csv", rows_for(astro, sid))
    # One JSON copy, to test JSON upload
    (OUT / "11_life_support_only.json").write_text(
        json.dumps({"rows": rows_for("SIM-LS-JSON", 8)}, indent=1), encoding="utf-8")
    # Validation test: some rows should be rejected
    bad = rows_for("SIM-BAD", 0)[:3]
    for r in bad:
        r["source"] = "USER-ENTERED"
    dup = dict(bad[1])                                    # duplicate of row 2
    future = dict(bad[2], timestamp="2027-06-01T00:00:00Z", mission_day=212)
    nonsense = dict(bad[2], timestamp="2026-11-05T00:00:00Z", mission_day=5, sleep_h=-3)
    write_csv(OUT / "12_validation_errors.csv", bad + [dup, future, nonsense])
    print(f"wrote {len(FILES) + 2} files to {OUT}")


if __name__ == "__main__":
    main()
`

## File: scripts/build_single_file.py

`python
#!/usr/bin/env python3
"""Build dist/orbitcare5x.html: one self-contained file (CSS, Chart.js, all JS modules inlined).

ES modules are rewritten into a tiny inline module registry (works from file://).
API base: window.ORBITCARE_API_BASE (from ?api=...) is prepended to every API path
by text-rewriting the bundled api.js / reports.js (frontend/ is never modified).
Usage: python scripts/build_single_file.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FE = ROOT / "frontend"
OUT = ROOT / "dist" / "orbitcare5x.html"

BASE_EXPR = "(window.ORBITCARE_API_BASE||'')"


def key_of(spec):
    return Path(spec).name.rsplit(".", 1)[0]


IMPORT_RE = re.compile(r"^import\s+(.+?)\s+from\s+['\"]([^'\"]+)['\"];?[ \t]*$", re.M)
EXPORT_DECL_RE = re.compile(r"^export\s+((?:async\s+)?function\s*\*?\s*|const\s+|let\s+|var\s+|class\s+)([A-Za-z_$][\w$]*)", re.M)


def convert(name, src):
    exports = []
    src = src.lstrip("﻿")

    def imp(m):
        clause, spec = m.group(1).strip(), m.group(2)
        if clause.startswith("* as "):
            return "const %s = __req(%r);" % (clause[5:].strip(), key_of(spec))
        clause = re.sub(r"\s+as\s+", ": ", clause)
        return "const %s = __req(%r);" % (clause, key_of(spec))

    src = IMPORT_RE.sub(imp, src)

    def exp(m):
        exports.append(m.group(2))
        return m.group(1) + m.group(2)

    src = EXPORT_DECL_RE.sub(exp, src)
    # dynamic imports
    src = re.sub(r"\bimport\(\s*([^)]+?)\s*\)", r"__imp(\1)", src)
    if re.search(r"^\s*(import|export)\s", src, re.M):
        sys.exit("unhandled import/export syntax in " + name)
    tail = "".join("__exp.%s = %s;\n" % (e, e) for e in exports)
    return "function(__exp, __req, __imp){\n%s\n%s}" % (src, tail)


def main():
    mods = {}
    for p in sorted((FE / "js").rglob("*.js")):
        if p.name == "app.js":
            continue
        text = p.read_text(encoding="utf-8")
        k = key_of(p.name)
        assert k not in mods, "duplicate module basename " + k
        if p.name == "api.js":
            assert "fetch(path, opts)" in text
            text = text.replace("fetch(path, opts)", "fetch(%s + path, opts)" % BASE_EXPR)
        if p.name == "reports.js":
            # get()/api() already prefix the base; only direct links need it
            text = re.sub(r"(\.href = )'(/api/[^']*)'", lambda m: "%s%s + '%s'" % (m.group(1), BASE_EXPR, m.group(2)), text)
            text = re.sub(r'href="(/api/[^"]*)"', lambda m: 'href="${%s}%s"' % (BASE_EXPR, m.group(1)), text)
            text = re.sub(r"href='(/api/[^']*)'", lambda m: "href='${%s}%s'" % (BASE_EXPR, m.group(1)), text)
        mods[k] = convert(p.name, text)
    app = convert("app.js", (FE / "js" / "app.js").read_text(encoding="utf-8"))

    registry = ",\n".join("%r: %s" % (k, v) for k, v in mods.items())
    runtime = """(function(){
'use strict';
var q = new URLSearchParams(location.search).get('api');
window.ORBITCARE_API_BASE = q ? q.replace(/\\/+$/, '') : '';
var bar = document.createElement('div');
bar.id = 'offline-banner'; bar.setAttribute('role', 'status');
bar.style.cssText = 'position:sticky;top:0;z-index:9999;padding:8px 14px;font:600 13px/1.4 system-ui,sans-serif;text-align:center;background:#fbbf24;color:#1f1300;';
bar.textContent = window.ORBITCARE_API_BASE
  ? 'Single-file build - API: ' + window.ORBITCARE_API_BASE
  : 'Offline single-file build \\u2014 connect to an ORBITCARE 5X server for data';
document.body.insertBefore(bar, document.body.firstChild);
var defs = {%s};
var cache = {};
function req(k){
  k = String(k).split('/').pop().replace(/\\.js$/, '');
  if (cache[k]) return cache[k];
  if (!defs[k]) throw new Error('Module not found: ' + k);
  var exp = cache[k] = {};
  defs[k](exp, req, imp);
  return exp;
}
function imp(s){ try { return Promise.resolve(req(s)); } catch (e) { return Promise.reject(e); } }
var appFn = %s;
appFn({}, req, imp);
})();""" % (registry, app)

    css = (FE / "css" / "theme.css").read_text(encoding="utf-8")
    chart = (FE / "vendor" / "chart.umd.min.js").read_text(encoding="utf-8")
    html = (FE / "index.html").read_text(encoding="utf-8")

    def esc_script(s):
        return re.sub(r"</(script)", r"<\\/\1", s, flags=re.I)

    html = re.sub(r'<link rel="stylesheet" href="/css/theme.css">', lambda m: "<style>\n" + css.replace("</style", "<\\/style") + "\n</style>", html)
    html = re.sub(r'<script src="/vendor/chart.umd.min.js"></script>', lambda m: "<script>\n" + esc_script(chart) + "\n</script>", html)
    html = re.sub(r'<script type="module" src="/js/app.js"></script>', lambda m: "<script>\n" + esc_script(runtime) + "\n</script>", html)
    assert "/css/theme.css" not in html.split("<style>")[0] and "/js/app.js" not in html[:3000] and "/vendor/" not in html[:3000], "external reference left"
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(html, encoding="utf-8", newline="\n")
    print("wrote %s (%d KB)" % (OUT, OUT.stat().st_size // 1024))


if __name__ == "__main__":
    main()
`

## File: backend/tests/test_grading.py

`python
﻿from backend.app.engine.config import DEFAULT_WEIGHTS, DEFAULT_CONFIG
from backend.app.engine.grading import (
    assess, status, grade_letter, score_radiation, score_mental_health, score_gravity,
    score_life_support, score_earth_distance, total_grade,
)


def nominal(**kw):
    r = {"timestamp": "2030-01-01T00:00:00Z", "astronaut_id": "SIM-A1", "mission_day": 1, "scenario_id": 0,
         "scenario_label": "Day-1 nominal", "cum_dose_msv": 0, "proton_flux_pfu": 0.1, "flare_active": 0,
         "sleep_h": 7.5, "hrv_rmssd_ms": 60, "hrv_baseline_ms": 60, "fatigue": 2, "stress": 2,
         "loading_index": 100, "loading_target": 100, "balance_score": 95,
         "cabin_o2_pct": 21, "cabin_co2_ppm": 800, "cabin_pressure_kpa": 101.3, "cabin_temp_c": 22,
         "cabin_humidity_pct": 45, "scrubber_state": "nominal", "latency_s": 1.3,
         "open_medical_flags": 0, "source": "SIMULATED"}
    r.update(kw)
    return r


def test_all_nominal():
    a = assess(nominal())
    for d in a["divisions"].values():
        assert d["score"] == 100.0 and d["status"] == "GREEN"
    t = a["total"]
    assert t["score"] == 100.0 and t["grade"] == "A+" and t["status"] == "GREEN"
    assert t["penalty"] == 0 and t["capped"] is False and t["delta_from_day1"] == 0.0


def test_string_inputs_accepted():
    r = {k: (str(v) if not isinstance(v, str) else v) for k, v in nominal(flare_active="1").items()}
    r["flare_active"] = "1"
    assert score_radiation(r)["score"] == 90.0  # 100 - 10 flare


def test_boundaries():
    for s, letter, st in [(100, "A+", "GREEN"), (95, "A+", "GREEN"), (94.9, "A", "GREEN"), (90, "A", "GREEN"),
                          (89.9, "B", "GREEN"), (75, "B", "GREEN"), (74.9, "C", "YELLOW"), (55, "C", "YELLOW"),
                          (54.9, "D", "YELLOW"), (35, "D", "YELLOW"), (34.9, "F", "RED"), (0, "F", "RED")]:
        assert grade_letter(s) == letter and status(s) == st, s
    assert status(None) == "NO_DATA" and grade_letter(None) is None


def test_weights_sum():
    assert abs(sum(DEFAULT_WEIGHTS.values()) - 1.0) < 1e-9
    assert "source" in DEFAULT_CONFIG["radiation"]["career_limit_msv"]


def test_single_division_30_bottleneck():
    # radiation: dose 600 -> -60, flare -10 => 30. weighted = .25*30 + .75*100 = 82.5 -> capped 54.9 (D)
    a = assess(nominal(cum_dose_msv=600, flare_active=1))
    assert a["divisions"]["radiation"]["score"] == 30.0
    t = a["total"]
    assert t["weighted"] == 82.5 and t["penalty"] == 0 and t["capped"] is True
    assert t["score"] == 54.9 and t["grade"] == "D"


def test_three_yellow_penalty():
    # radiation 60 (dose 400 -> -40... use 600 dose -> 40), mental: sleep 4.5 -25, fatigue 10 -20 => 55
    # gravity: ratio .5 -> -30, balance 45 -> -30 (cap) => 40. others 100 (earth tier1)
    a = assess(nominal(cum_dose_msv=600, sleep_h=4.5, fatigue=10, loading_index=50, balance_score=45))
    d = {k: v["score"] for k, v in a["divisions"].items()}
    assert d == {"radiation": 40.0, "mental_health": 55.0, "gravity": 40.0, "life_support": 100.0, "earth_distance": 100.0}
    # weighted = .25*40 + .20*55 + .15*40 + .25*100 + .15*100 = 10+11+6+25+15 = 67 ; penalty -10 -> 57
    t = a["total"]
    assert t["weighted"] == 67.0 and t["penalty"] == -10 and t["score"] == 57.0 and not t["capped"]
    assert t["grade"] == "C"


def test_penalty_and_cap_together():
    # radiation 10 (RED), mental 55, gravity 40: weighted = 2.5+11+6+25+15 = 59.5; -10 = 49.5 (<54.9 so cap no change)
    a = assess(nominal(cum_dose_msv=600, proton_flux_pfu=12, flare_active=1, sleep_h=4.5, fatigue=10,
                       loading_index=50, balance_score=45))
    t = a["total"]
    assert a["divisions"]["radiation"]["score"] == 10.0
    assert t["weighted"] == 59.5 and t["penalty"] == -10 and t["capped"] is True and t["score"] == 49.5
    # cap actually binds: weighted high
    divs = {"radiation": {"score": 20.0, "status": "RED"}, "mental_health": {"score": 70.0, "status": "YELLOW"},
            "gravity": {"score": 70.0, "status": "YELLOW"}, "life_support": {"score": 100.0, "status": "GREEN"},
            "earth_distance": {"score": 100.0, "status": "GREEN"}}
    # weighted = 5+14+10.5+25+15 = 69.5; -10 = 59.5 -> cap 54.9
    t = total_grade(divs)
    assert t["weighted"] == 69.5 and t["score"] == 54.9 and t["capped"] and t["grade"] == "D"


def test_radiation_extreme():
    r = score_radiation(nominal(cum_dose_msv=600, proton_flux_pfu=12, flare_active=1))
    assert r["score"] == 10.0 and r["status"] == "RED" and r["grade"] == "F"
    assert [f["code"] for f in r["factors"]] and all({"code", "label", "value", "deduction"} <= set(f) for f in r["factors"])
    # dose 300 -> 30 deduction; proton 9.9 below threshold
    assert score_radiation(nominal(cum_dose_msv=300, proton_flux_pfu=9.9))["score"] == 70.0
    assert score_radiation(nominal(cum_dose_msv=1200))["score"] == 40.0  # capped at 60


def test_other_division_formulas():
    # sleep 5.5 -15; hrv 45/60 -> 25% drop -25; fatigue 7 -> 8; stress 6 -> 4 => 100-52 = 48
    assert score_mental_health(nominal(sleep_h=5.5, hrv_rmssd_ms=45, fatigue=7, stress=6))["score"] == 48.0
    assert score_mental_health(nominal(hrv_baseline_ms="", hrv_rmssd_ms=10))["score"] == 100.0  # no baseline
    # ratio .7 -> -10 ; balance 75 -> -8 => 82
    assert score_gravity(nominal(loading_index=70, balance_score=75))["score"] == 82.0
    # co2 5500 -> 10; o2 18.5 -> 15; pressure 94 -> 12; scrubber offline 35 => 28
    assert score_life_support(nominal(cabin_co2_ppm=5500, cabin_o2_pct=18.5, cabin_pressure_kpa=94,
                                      scrubber_state="offline"))["score"] == 28.0
    assert score_life_support(nominal(scrubber_state="degraded"))["score"] == 85.0


def test_earth_distance_tier3_conditional():
    # all others green -> no latency deduction
    assert assess(nominal(latency_s=900))["divisions"]["earth_distance"]["score"] == 100.0
    # radiation 40 YELLOW + tier3 -> -30 => 70
    a = assess(nominal(latency_s=900, cum_dose_msv=600))
    assert a["divisions"]["earth_distance"]["score"] == 70.0
    a = assess(nominal(latency_s=30, cum_dose_msv=600))  # tier 2 -> -15
    assert a["divisions"]["earth_distance"]["score"] == 85.0


def test_open_flags_cap():
    assert assess(nominal(open_medical_flags=2))["divisions"]["earth_distance"]["score"] == 90.0
    assert assess(nominal(open_medical_flags="9"))["divisions"]["earth_distance"]["score"] == 80.0  # max -20


def test_no_data_renormalised():
    r = nominal(latency_s="", open_medical_flags="", cum_dose_msv=600)
    a = assess(r)
    assert a["divisions"]["earth_distance"]["status"] == "NO_DATA" and a["divisions"]["earth_distance"]["score"] is None
    # radiation 40, others 100; weights excl earth: .25*40+.25*100+.2*100+.15*100 = 70 / .85 = 82.35 -> 82.4
    assert a["total"]["weighted"] == 82.4
    # entire division null
    r = nominal(cabin_o2_pct="", cabin_co2_ppm="", cabin_pressure_kpa="", scrubber_state="")
    assert assess(r)["divisions"]["life_support"]["status"] == "NO_DATA"


def test_delta_from_day1():
    a = assess(nominal(cum_dose_msv=600), day1_score=100.0)
    assert a["total"]["delta_from_day1"] == a["total"]["score"] - 100.0
    a = assess(nominal(), day1_score=90.0)
    assert a["total"]["delta_from_day1"] == 10.0


def test_assess_label_and_interaction_flags():
    a = assess(nominal(cum_dose_msv=600, sleep_h=4.5, fatigue=10))
    assert a["label"] == "Readiness & Condition Index \u2014 Illustrative screening metric, not a medical diagnosis"
    assert a["astronaut_id"] == "SIM-A1" and a["mission_day"] == 1 and a["source"] == "SIMULATED"
    assert [f["pair"] for f in a["interaction_flags"]] == [["radiation", "mental_health"]]
    assert a["interaction_flags"][0]["label"] == "Hypothesis from HRP hazard descriptions"
    assert assess(nominal())["interaction_flags"] == []
    assert list(a["divisions"]) == ["radiation", "mental_health", "gravity", "life_support", "earth_distance"]
`

## File: backend/tests/test_api.py

`python
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
`

## File: backend/tests/test_settings_reports.py

`python
﻿import json

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
`

## File: backend/tests/test_spaceweather.py

`python
﻿import httpx
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
`

## File: backend/tests/test_telemetry_raw.py

`python
﻿from backend.tests.test_api import client, upload_csv  # noqa: F401


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
`

## File: backend/tests/test_cors.py

`python
﻿from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_null_origin_get_allowed():
    r = client.get("/api/health", headers={"Origin": "null"})
    assert r.headers.get("access-control-allow-origin") == "null"
    assert "access-control-allow-credentials" not in r.headers


def test_null_origin_preflight_allowed():
    r = client.options(
        "/api/health",
        headers={"Origin": "null", "Access-Control-Request-Method": "GET"},
    )
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "null"


def test_evil_origin_denied():
    r = client.get("/api/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in r.headers
    r = client.options(
        "/api/health",
        headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in r.headers
`

## File: frontend/index.html

`html
﻿<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ORBITCARE 5X</title>
  <link rel="stylesheet" href="/css/theme.css">
</head>
<body>
  <a class="skip" href="#view">Skip to content</a>
  <div class="shell">
    <aside class="sidebar" id="sidebar" aria-label="Primary">
      <div class="brand"><span class="logo" aria-hidden="true">5X</span><span>ORBITCARE <b>5X</b></span></div>
      <nav id="nav"></nav>
    </aside>
    <div class="mobilebar" id="mobilebar">
      <button id="drawerBtn" aria-expanded="false" aria-controls="sidebar">Menu</button>
      <span class="brand-sm">ORBITCARE 5X</span>
    </div>
    <div class="main">
      <main id="view" tabindex="-1" aria-live="polite"></main>
      <footer class="footer" id="footer">
        <p>ORBITCARE 5X is not a medical device or diagnostic system. Readiness &amp; Condition Index &mdash; Illustrative screening metric, not a medical diagnosis. Demo crew data is SIMULATED.</p>
      </footer>
    </div>
  </div>
  <script src="/vendor/chart.umd.min.js"></script>
  <script type="module" src="/js/app.js"></script>
</body>
</html>
`

## File: frontend/css/theme.css

`css
﻿:root{--bg:#050b1a;--panel:#0b1630;--panel2:#101f40;--line:#1e3358;--text:#e8f1ff;--muted:#9db3d6;--cyan:#22d3ee;--cyan-d:#0e7490;
--green:#22c55e;--yellow:#facc15;--red:#ff4d4d;--nodata:#8090ac;--radius:10px;}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,Segoe UI,Roboto,sans-serif}
a{color:var(--cyan)}
.skip{position:absolute;left:-999px}.skip:focus{left:8px;top:8px;background:#000;padding:6px;z-index:99}
:focus-visible{outline:2px solid var(--cyan);outline-offset:2px}
.shell{display:flex;min-height:100vh}
.sidebar{width:230px;flex:none;background:#070f24;border-right:1px solid var(--line);padding:14px 10px;position:sticky;top:0;height:100vh;overflow:auto}
.brand{display:flex;gap:10px;align-items:center;font-weight:600;letter-spacing:.08em;margin:4px 8px 16px}
.brand b{color:var(--cyan)}.logo{background:var(--cyan);color:#001018;border-radius:6px;padding:2px 6px;font-weight:800}
.sidebar nav a{display:block;padding:8px 12px;border-radius:8px;color:var(--muted);text-decoration:none;margin-bottom:2px}
.sidebar nav a:hover{background:var(--panel2);color:var(--text)}
.sidebar nav a[aria-current=page]{background:var(--cyan-d);color:#fff;font-weight:600}
.sidebar nav a small{display:block;font-size:11px;color:var(--nodata)}
.mobilebar{display:none}
.main{flex:1;min-width:0;display:flex;flex-direction:column}
main{padding:20px 24px;flex:1;max-width:1280px;width:100%}
.footer{border-top:1px solid var(--line);padding:12px 24px;color:var(--muted);font-size:12px}
.footer p{margin:0}
h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:0 0 10px;color:var(--cyan)}
.sub{color:var(--muted);margin:0 0 16px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:16px;margin-bottom:16px}
.grid{display:grid;gap:12px}.g5{grid-template-columns:repeat(auto-fit,minmax(170px,1fr))}.g2{grid-template-columns:repeat(auto-fit,minmax(320px,1fr))}
.row{display:flex;flex-wrap:wrap;gap:10px;align-items:center}
.spacer{flex:1}
button,.btn,select,input{font:inherit}
button,.btn{background:var(--panel2);color:var(--text);border:1px solid var(--cyan-d);border-radius:8px;padding:7px 14px;cursor:pointer}
button:hover{border-color:var(--cyan)}button.primary{background:var(--cyan);color:#001018;border-color:var(--cyan);font-weight:600}
button[aria-pressed=true]{background:var(--green);color:#00140a;border-color:var(--green);font-weight:700}
button:disabled{opacity:.5;cursor:not-allowed}
select,input[type=file]{background:var(--panel2);color:var(--text);border:1px solid var(--line);border-radius:8px;padding:6px}
.tile{border:2px solid var(--line);border-left-width:8px;border-radius:var(--radius);padding:12px;background:var(--panel2)}
.tile .name{color:var(--muted);font-size:13px}.tile .score{font-size:30px;font-weight:700}.tile .letter{font-size:20px;font-weight:700;margin-left:8px}
.st-GREEN{border-color:var(--green)}.st-YELLOW{border-color:var(--yellow)}.st-RED{border-color:var(--red)}.st-NO_DATA{border-color:var(--nodata)}
.pill{display:inline-block;border-radius:999px;padding:1px 10px;font-size:12px;font-weight:700;border:1px solid}
.pill.GREEN{color:var(--green)}.pill.YELLOW{color:var(--yellow)}.pill.RED{color:var(--red)}.pill.NO_DATA{color:var(--nodata)}
.src{display:inline-block;font-size:10px;letter-spacing:.06em;padding:0 6px;border-radius:4px;border:1px solid var(--cyan-d);color:var(--cyan);vertical-align:middle;margin-left:6px;font-weight:700}
.src.LIVE{color:var(--green);border-color:var(--green)}.src.FAILED{color:var(--red);border-color:var(--red)}
.total{display:flex;gap:18px;align-items:center;flex-wrap:wrap}
.badge{min-width:150px;text-align:center;border:3px solid var(--line);border-radius:16px;padding:10px 18px;background:var(--panel2)}
.badge .big{font-size:46px;font-weight:800;line-height:1}.badge .lt{font-size:22px;font-weight:700}
.flag{display:inline-block;border-radius:6px;padding:2px 10px;font-size:13px;font-weight:600;margin:2px 6px 2px 0}
.flag.warn{background:#3a2f05;color:var(--yellow);border:1px solid var(--yellow)}
.flag.bad{background:#3d0d0d;color:#ff8a8a;border:1px solid var(--red)}
.delta.neg{color:var(--red)}.delta.pos{color:var(--green)}
.muted{color:var(--muted)}
.err{border:2px solid var(--red);background:#2a0c10;border-radius:var(--radius);padding:14px;margin-bottom:16px}
.err b{color:#ff8a8a}
.empty,.nc{border:2px dashed var(--line);border-radius:var(--radius);padding:24px;text-align:center;color:var(--muted)}
.nc b{color:var(--yellow)}
.loading{color:var(--muted);padding:16px}.loading::before{content:"";display:inline-block;width:12px;height:12px;border:2px solid var(--cyan);border-top-color:transparent;border-radius:50%;margin-right:8px;animation:sp 1s linear infinite}
@keyframes sp{to{transform:rotate(360deg)}}
table{border-collapse:collapse;width:100%;font-size:13px}th,td{border-bottom:1px solid var(--line);padding:5px 8px;text-align:left}th{color:var(--muted);font-weight:600}
.bar{height:16px;background:#0a1328;border:1px solid var(--line);border-radius:6px;overflow:hidden}.bar>i{display:block;height:100%}
.bar.GREEN>i{background:var(--green)}.bar.YELLOW>i{background:var(--yellow)}.bar.RED>i{background:var(--red)}.bar.NO_DATA>i{background:var(--nodata)}
.bars{display:grid;grid-template-columns:150px 1fr 120px;gap:8px 10px;align-items:center}
.chartbox{position:relative;height:320px}
ul.clean{margin:4px 0;padding-left:18px}
.hud .badge .big{font-size:64px}.hud{font-size:16px}
details summary{cursor:pointer;color:var(--cyan)}
@media (max-width:979px){
 .shell{display:block}
 .mobilebar{display:flex;position:fixed;bottom:0;left:0;right:0;z-index:20;background:#070f24;border-top:1px solid var(--line);padding:8px 12px;gap:12px;align-items:center}
 .sidebar{position:fixed;top:0;left:0;bottom:48px;height:auto;z-index:30;transform:translateX(-105%);transition:transform .2s;width:260px}
 .sidebar.open{transform:none}
 main{padding:14px 12px 70px}.footer{padding-bottom:64px}
 .bars{grid-template-columns:110px 1fr}.bars .fv{grid-column:1/-1}
}

.gtabs{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0 14px}
.gtabs a{padding:6px 12px;border:1px solid var(--line);border-radius:8px;text-decoration:none;color:var(--muted)}
.gtabs a[aria-current=page]{background:var(--cyan-d);color:#fff;border-color:var(--cyan)}
#triout ol{margin:10px 0 0;padding-left:20px}
`

## File: frontend/js/api.js

`javascript
﻿export async function api(path, opts = {}) {
  let res;
  try {
    res = await fetch(path, opts);
  } catch (e) {
    throw new Error('Cannot reach the backend API (' + path + '): ' + (e && e.message ? e.message : e));
  }
  let body = null;
  try { body = await res.json(); } catch (_) { /* non-JSON */ }
  if (!res.ok) {
    const d = body && body.detail;
    throw new Error((typeof d === 'string' ? d : d ? JSON.stringify(d) : 'HTTP ' + res.status) + ' (' + path + ')');
  }
  return body;
}
export const get = (p) => api(p);
export const postJson = (p, data) => api(p, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
export const postFile = (p, file) => { const f = new FormData(); f.append('file', file); return api(p, { method: 'POST', body: f }); };
`

## File: frontend/js/app.js

`javascript
﻿import { notConnected, esc } from './ui.js';
import * as mission from './pages/mission-control.js';
import * as hud from './pages/hud.js';
import * as guards from './pages/guards.js';

const SECTIONS = [
  { id: 'mission-control', title: 'Mission Control', page: mission },
  { id: 'space-weather', title: 'Space Weather', dyn: './pages/spaceweather.js' },
  { id: 'radiation-guard', title: 'Radiation Guard', page: guards, opts: { key: 'radiation' } },
  { id: 'crew-health', title: 'Crew Health', page: hud, opts: { mode: 'crew' } },
  { id: 'mental-health-guard', title: 'Mental Health Guard', page: guards, opts: { key: 'mental_health' } },
  { id: 'gravity-guard', title: 'Gravity Health Guard', page: guards, opts: { key: 'gravity' } },
  { id: 'life-support-guard', title: 'Life Support Guard', page: guards, opts: { key: 'life_support' } },
  { id: 'earth-distance-guard', title: 'Earth Distance Guard', page: guards, opts: { key: 'earth_distance' } },
  { id: 'ai-risk', title: 'AI Risk Analysis', dyn: './pages/ai-risk.js' },
  { id: 'flight-surgeon-hud', title: 'Flight Surgeon HUD', page: hud, opts: { mode: 'hud' } },
  { id: 'mission-simulator', title: 'Mission Simulator', dyn: './pages/simulator.js' },
  { id: 'alerts', title: 'Alerts Centre', dyn: './pages/alerts.js' },
  { id: 'reports', title: 'Reports & Analytics', dyn: './pages/reports.js' },
  { id: 'settings', title: 'Settings', dyn: './pages/settings.js' },
];

const view = document.getElementById('view');
const nav = document.getElementById('nav');
const sidebar = document.getElementById('sidebar');
const drawerBtn = document.getElementById('drawerBtn');
let cleanup = null;
let routeToken = 0;

nav.innerHTML = SECTIONS.map((s, i) => `<a href="#/${s.id}" data-id="${s.id}">${i + 1}. ${esc(s.title)}${s.sub ? `<small>${esc(s.sub)}</small>` : ''}</a>`).join('');
drawerBtn.onclick = () => { const o = sidebar.classList.toggle('open'); drawerBtn.setAttribute('aria-expanded', o); };

function route() {
  const id = (location.hash.replace(/^#\/?/, '') || SECTIONS[0].id);
  const sec = SECTIONS.find((s) => s.id === id) || SECTIONS[0];
  if (typeof cleanup === 'function') { try { cleanup(); } catch (_) { /* ignore */ } }
  cleanup = null;
  sidebar.classList.remove('open'); drawerBtn.setAttribute('aria-expanded', 'false');
  nav.querySelectorAll('a').forEach((a) => (a.dataset.id === sec.id ? a.setAttribute('aria-current', 'page') : a.removeAttribute('aria-current')));
  document.title = sec.title + ' - ORBITCARE 5X';
  const token = ++routeToken;
  if (sec.page) {
    cleanup = sec.page.render(view, sec.opts || {}) || null;
    if (cleanup && typeof cleanup.then === 'function') { const p = cleanup; cleanup = null; p.then((c) => { if (token === routeToken) cleanup = c; else if (typeof c === 'function') c(); }).catch(() => {}); }
  } else if (sec.dyn) {
    view.innerHTML = '<p class="loading">Loading...</p>';
    import(sec.dyn).then((m) => { if (token !== routeToken) return; view.innerHTML = ''; return Promise.resolve(m.render(view)).then((c) => { if (token === routeToken) cleanup = c || null; else if (typeof c === 'function') c(); }); })
      .catch((e) => { if (token === routeToken) view.innerHTML = notConnected(sec.title, sec.sub || '') + (e && e.message ? '<p class="muted">' + esc(e.message) + '</p>' : ''); });
  } else {
    view.innerHTML = notConnected(sec.title, sec.sub || '');
  }
  window.scrollTo(0, 0);
}
window.addEventListener('hashchange', route);
route();
`

## File: frontend/js/ui.js

`javascript
﻿export const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export const DIV_ORDER = ['radiation', 'earth_distance', 'gravity', 'life_support', 'mental_health'];
export const DIV_NAMES = { radiation: 'Radiation', earth_distance: 'Distance', gravity: 'Gravity', life_support: 'Closed Ecosystem', mental_health: 'Isolation & Stress' };
export const DIV_COLORS = { total: '#22d3ee', radiation: '#f472b6', earth_distance: '#a78bfa', gravity: '#fb923c', life_support: '#34d399', mental_health: '#60a5fa' };
export const src = (s) => `<span class="src ${esc(s)}" title="Data source">${esc(s || 'SIMULATED')}</span>`;
export const pill = (st) => `<span class="pill ${esc(st)}">${esc(st)}</span>`;
export const fmt = (n, d = 1) => (n === null || n === undefined || Number.isNaN(n)) ? '--' : Number(n).toFixed(d);
export const loading = (t = 'Loading...') => `<div class="loading" role="status">${esc(t)}</div>`;
export function errorPanel(root, err, retry) {
  const d = document.createElement('div');
  d.className = 'err'; d.setAttribute('role', 'alert');
  d.innerHTML = `<b>Backend unavailable or request failed.</b><p>${esc(err && err.message ? err.message : err)}</p><button class="primary">Retry</button>`;
  d.querySelector('button').onclick = retry;
  root.replaceChildren(d);
}
export const notConnected = (title, blurb) => `<h1>${esc(title)}</h1><p class="sub">${esc(blurb || '')}</p>
<div class="nc"><b>Not connected yet</b> &mdash; planned in a later milestone. No data is shown here and none is fabricated.</div>`;
export function drawChart(canvas, assessments, existing) {
  if (existing) existing.destroy();
  if (!window.Chart) { canvas.replaceWith(Object.assign(document.createElement('p'), { className: 'muted', textContent: 'Chart library failed to load.' })); return null; }
  const labels = assessments.map((a) => a.mission_day);
  const ds = [{ label: 'Total', data: assessments.map((a) => a.total.score), borderColor: DIV_COLORS.total, borderWidth: 4, tension: .2, pointRadius: 2 }];
  for (const k of DIV_ORDER) ds.push({ label: DIV_NAMES[k], data: assessments.map((a) => a.divisions[k] ? a.divisions[k].score : null), borderColor: DIV_COLORS[k], borderWidth: 1.5, tension: .2, pointRadius: 0, spanGaps: true });
  Chart.defaults.color = '#9db3d6';
  return new Chart(canvas, { type: 'line', data: { labels, datasets: ds }, options: { responsive: true, maintainAspectRatio: false, animation: false,
    scales: { y: { min: 0, max: 100, title: { display: true, text: 'Score (0-100)' }, grid: { color: '#1e3358' } }, x: { title: { display: true, text: 'mission_day' }, grid: { color: '#1e3358' } } },
    plugins: { legend: { labels: { color: '#e8f1ff' } } } } });
}
export function breakdown(a) {
  return `<div class="bars">${DIV_ORDER.map((k) => { const d = a.divisions[k] || {}; const s = d.score;
    return `<div>${esc(DIV_NAMES[k])}</div><div class="bar ${esc(d.status)}" role="img" aria-label="${esc(DIV_NAMES[k])} ${fmt(s)}"><i style="width:${s == null ? 0 : s}%"></i></div><div class="fv">${fmt(s)} ${esc(d.grade || '')} ${pill(d.status || 'NO_DATA')}${src(a.source)}</div>`; }).join('')}</div>`;
}
`

## File: frontend/js/pages/mission-control.js

`javascript
﻿import { get, postJson, postFile } from '../api.js';
import { esc, DIV_ORDER, DIV_NAMES, src, pill, fmt, loading, errorPanel, drawChart } from '../ui.js';

const PLANNED_DAYS = 32; // illustrative default planned duration (ESTIMATE)

export function render(root) {
  let timer = null, chart = null, dead = false;
  let astro = null, report = null, streamMsg = '';
  const stop = () => { if (timer) { clearInterval(timer); timer = null; } };

  async function load() {
    root.innerHTML = `<h1>Mission Control</h1>${loading('Loading mission data from API...')}`;
    try {
      const crew = (await get('/api/crew')).items || [];
      const latest = (await get('/api/assessments/latest')).items || [];
      if (dead) return;
      if (!astro || !crew.concat(latest).some((c) => c.astronaut_id === astro)) astro = (latest[0] || crew[0] || {}).astronaut_id || null;
      const traj = astro ? (await get('/api/assessments?astronaut_id=' + encodeURIComponent(astro))).items || [] : [];
      if (dead) return;
      draw(crew, latest, traj);
    } catch (e) { if (!dead) errorPanel(root, e, load); }
  }

  function draw(crew, latest, traj) {
    const cur = traj.length ? traj[traj.length - 1] : (latest.find((l) => l.astronaut_id === astro) || null);
    const ids = [...new Set(crew.map((c) => c.astronaut_id).concat(latest.map((l) => l.astronaut_id)))];
    const day = cur ? cur.mission_day : 0;
    let h = `<h1>Mission Control</h1><p class="sub">Readiness &amp; Condition Index &mdash; Illustrative screening metric, not a medical diagnosis.</p>`;
    h += `<div class="panel"><div class="row"><div><b>Mission day ${day || '--'} of ${PLANNED_DAYS}</b>${src(cur ? cur.source : 'ESTIMATE')} <span class="muted">(planned duration ${PLANNED_DAYS} d: illustrative default${cur ? '; MET from latest telemetry' : ''})</span></div><span class="spacer"></span>
      <label>Astronaut <select id="astro">${ids.length ? ids.map((i) => `<option ${i === astro ? 'selected' : ''}>${esc(i)}</option>`).join('') : '<option>none</option>'}</select></label></div>
      <div class="bar" style="margin-top:10px" aria-label="Mission progress"><i style="width:${Math.min(100, day / PLANNED_DAYS * 100)}%;background:var(--cyan)"></i></div></div>`;
    h += `<div class="panel"><h2>Workflow A upload</h2><div class="row"><input type="file" id="file" accept=".csv,.json" aria-label="Telemetry file"><button class="primary" id="up">Upload &amp; run 7-stage pipeline</button>
      <button id="stream" aria-pressed="${!!timer}">Live Simulation Stream: ${timer ? 'ON' : 'OFF'}</button><button id="reset" title="DELETE /api/telemetry">Reset demo data</button></div>
      <p class="muted" id="smsg" role="status">${esc(streamMsg)}</p><div id="report">${reportHtml()}</div></div>`;
    if (!cur) {
      h += `<div class="empty"><b>No telemetry yet.</b><br>Upload data/sample/workflow_a_31_scenarios.csv or start the Live Simulation Stream.</div>`;
    } else {
      const t = cur.total, dl = t.delta_from_day1;
      h += `<div class="panel"><h2>Total Mission Grade</h2><div class="total"><div class="badge st-${esc(t.status)}"><div class="big">${fmt(t.score)}</div><div class="lt">Grade ${esc(t.grade)}</div>${pill(t.status)}</div>
        <div><div>Delta from Day 1: <b class="delta ${dl < 0 ? 'neg' : 'pos'}">${dl > 0 ? '+' : ''}${fmt(dl)}</b>${src(cur.source)}</div>
        <div>Weighted: ${fmt(t.weighted)}${src(cur.source)}</div>
        <div>${t.capped ? '<span class="flag bad">Capped by bottleneck (a division &lt; 35: total cannot exceed D)</span>' : ''}${t.penalty < 0 ? `<span class="flag warn">${fmt(t.penalty, 0)} compounding (3+ divisions YELLOW/RED)</span>` : ''}${!t.capped && t.penalty >= 0 ? '<span class="muted">No cap or compounding penalty applied.</span>' : ''}</div></div></div>`;
      h += `<div class="panel"><h2>Five Hazards</h2><div class="grid g5">${DIV_ORDER.map((k) => { const d = cur.divisions[k] || {};
        return `<div class="tile st-${esc(d.status)}"><div class="name">${esc(DIV_NAMES[k])}</div><div><span class="score">${fmt(d.score)}</span><span class="letter">${esc(d.grade || '')}</span></div>${pill(d.status || 'NO_DATA')}${src(cur.source)}</div>`; }).join('')}</div></div>`;
      if ((cur.interaction_flags || []).length) h += `<div class="panel"><h2>Interaction watch</h2>${cur.interaction_flags.map((f) => `<span class="flag warn">${esc(f.pair.map((p) => DIV_NAMES[p] || p).join(' + '))}</span>`).join('')}<p class="muted">${esc(cur.interaction_flags[0].label || 'Hypothesis from HRP hazard descriptions')}</p></div>`;
    }
    h += `<div class="panel"><h2>Grade Trajectory Overlay</h2>${traj.length ? `<div class="chartbox"><canvas id="ch" role="img" aria-label="Grade trajectory"></canvas></div>` : '<div class="empty">No trajectory yet.</div>'}</div>`;
    h += `<div class="panel"><h2>Crew</h2>${latest.length ? `<table><tr><th>Astronaut</th><th>Day</th><th>Total</th><th>Grade</th><th>Source</th></tr>${latest.map((l) => `<tr><td>${esc(l.astronaut_id)}</td><td>${l.mission_day}</td><td>${fmt(l.total.score)}</td><td>${esc(l.total.grade)}</td><td>${src(l.source)}</td></tr>`).join('')}</table>` : '<span class="muted">No crew assessments yet.</span>'}</div>`;
    root.innerHTML = h;
    if (traj.length) chart = drawChart(root.querySelector('#ch'), traj, chart);
    wire(cur);
  }

  function reportHtml() {
    if (!report) return '';
    const r = report;
    return `<p><b>Received ${r.received}</b> &middot; accepted <b>${r.accepted}</b> &middot; rejected <b>${(r.rejected || []).length}</b> &middot; suspect <b>${(r.suspect || []).length}</b> ${src('USER-ENTERED')}</p>
      ${(r.rejected || []).length ? `<details><summary>Rejected rows</summary><ul class="clean">${r.rejected.map((x) => `<li>row ${x.row}: ${esc(x.reason)}</li>`).join('')}</ul></details>` : ''}
      ${(r.suspect || []).length ? `<details><summary>Suspect values</summary><ul class="clean">${r.suspect.map((x) => `<li>row ${x.row} ${esc(x.metric)}: ${esc(x.reason)}</li>`).join('')}</ul></details>` : ''}
      <table><tr><th>#</th><th>Stage</th><th>In</th><th>Out</th><th>Rejected</th><th>Last run</th><th>Notes</th></tr>${(r.pipeline || []).map((s) => `<tr><td>${s.stage}</td><td>${esc(s.name)}</td><td>${s.records_in}</td><td>${s.records_out}</td><td>${s.rejected}</td><td>${esc(s.last_run)}</td><td>${esc(s.notes)}</td></tr>`).join('')}</table>`;
  }

  function wire(cur) {
    const q = (s) => root.querySelector(s);
    q('#astro').onchange = (e) => { astro = e.target.value; load(); };
    q('#up').onclick = async () => {
      const f = q('#file').files[0];
      if (!f) { q('#smsg').textContent = 'Choose a .csv or .json file first.'; return; }
      q('#up').disabled = true; q('#smsg').textContent = 'Uploading...';
      try { report = await postFile('/api/telemetry/upload', f); streamMsg = 'Upload complete.'; await load(); }
      catch (e) { q('#up').disabled = false; q('#smsg').textContent = 'Upload failed: ' + e.message; }
    };
    q('#reset').onclick = async () => {
      if (!confirm('Delete all demo telemetry?')) return;
      try { await api_delete(); report = null; streamMsg = 'Demo data reset.'; await load(); } catch (e) { q('#smsg').textContent = 'Reset failed: ' + e.message; }
    };
    q('#stream').onclick = () => {
      if (timer) { stop(); streamMsg = 'Stream stopped.'; } else { timer = setInterval(tick, 4000); streamMsg = 'Stream running (every 4 s)...'; tick(); }
      const b = q('#stream'); b.setAttribute('aria-pressed', !!timer); b.textContent = 'Live Simulation Stream: ' + (timer ? 'ON' : 'OFF'); q('#smsg').textContent = streamMsg;
    };
  }

  let busy = false;
  async function tick() {
    if (busy || dead) return; busy = true;
    try {
      const id = astro || 'SIM-A1';
      const hist = (await get('/api/assessments?astronaut_id=' + encodeURIComponent(id))).items || [];
      const day = (hist.length ? hist[hist.length - 1].mission_day : 0) + 1;
      const row = await get(`/api/telemetry/simulate?astronaut_id=${encodeURIComponent(id)}&day=${day}&scenario_id=${(day - 1) % 32}`);
      report = await postJson('/api/telemetry/ingest', { rows: [row] });
      streamMsg = `Streamed day ${day} (SIMULATED).`;
      if (!dead) await load();
    } catch (e) { stop(); streamMsg = 'Stream stopped: ' + e.message; if (!dead) await load(); }
    finally { busy = false; }
  }
  async function api_delete() { const { api } = await import('../api.js'); return api('/api/telemetry', { method: 'DELETE' }); }

  load();
  return () => { dead = true; stop(); if (chart) chart.destroy(); };
}
`

## File: frontend/js/pages/simulator.js

`javascript
﻿import { postJson } from '../api.js';
import { esc, fmt, pill, DIV_ORDER, DIV_NAMES } from '../ui.js';

const FIELDS = [
  ['Radiation', [['cum_dose_msv', 'Cumulative dose (mSv)', 0, 1000, 1, 0], ['proton_flux_pfu', 'Proton flux (pfu)', 0, 100, 1, 0], ['flare_active', 'Solar flare active', 'bool', 0]]],
  ['Isolation & Stress', [['sleep_h', 'Sleep (h)', 0, 12, 0.1, 8], ['hrv_rmssd_ms', 'HRV RMSSD (ms)', 0, 150, 1, 60], ['hrv_baseline_ms', 'HRV baseline (ms)', 20, 150, 1, 60], ['fatigue', 'Fatigue (0-10)', 0, 10, 0.1, 2], ['stress', 'Stress (0-10)', 0, 10, 0.1, 2]]],
  ['Gravity', [['loading_index', 'Loading index', 0, 2, 0.01, 1], ['loading_target', 'Loading target', 0.5, 2, 0.01, 1], ['balance_score', 'Balance score (0-100)', 0, 100, 1, 95]]],
  ['Closed Ecosystem', [['cabin_o2_pct', 'Cabin O2 (%)', 15, 30, 0.1, 21], ['cabin_co2_ppm', 'Cabin CO2 (ppm)', 0, 10000, 50, 500], ['cabin_pressure_kpa', 'Cabin pressure (kPa)', 80, 120, 0.5, 101], ['scrubber_state', 'Scrubber state', 'select', 'nominal']]],
  ['Distance', [['latency_s', 'Comm latency (s)', 0, 1500, 1, 1], ['open_medical_flags', 'Open medical flags', 0, 6, 1, 0]]],
];

export async function render(el) {
  const vals = { astronaut_id: 'WHAT-IF', mission_day: 10, scenario_id: 0, scenario_label: 'what-if', timestamp: '2026-11-10T00:00:00Z', source: 'SIMULATED', cabin_temp_c: 22, cabin_humidity_pct: 45 };
  for (const [, fs] of FIELDS) for (const f of fs) vals[f[0]] = f[2] === 'bool' ? f[3] : f[2] === 'select' ? f[3] : f[5];
  const ctl = (f) => {
    const [k, label, a, b, step] = f;
    if (a === 'bool') return `<label class="row"><input type="checkbox" data-k="${k}"> ${esc(label)}</label>`;
    if (a === 'select') return `<label>${esc(label)} <select data-k="${k}"><option>nominal</option><option>degraded</option><option>offline</option></select></label>`;
    return `<label style="display:block">${esc(label)}: <b data-v="${k}">${vals[k]}</b><input type="range" data-k="${k}" min="${a}" max="${b}" step="${step}" value="${vals[k]}" style="width:100%"></label>`;
  };
  el.innerHTML = `<h1>Mission Simulator</h1>
<p class="sub"><span class="src SIMULATED">SIMULATED</span> What-if sandbox. Values below are hypothetical, are not stored, and do not change any crew record. Uses the current grading weights and thresholds from Settings.</p>
<div class="grid g2"><div class="panel"><h2>Hazard inputs</h2>${FIELDS.map(([t, fs]) => `<fieldset style="border:1px solid var(--line);border-radius:8px;margin-bottom:10px"><legend>${esc(t)}</legend>${fs.map(ctl).join('')}</fieldset>`).join('')}<button id="rst">Reset to nominal</button></div>
<div class="panel" id="out" aria-live="polite"><p class="loading">Calculating...</p></div></div>`;
  const out = el.querySelector('#out');
  let timer = null, seq = 0, dead = false;
  async function calc() {
    const my = ++seq;
    try {
      const a = await postJson('/api/simulate/assess', { row: vals });
      if (dead || my !== seq) return;
      const t = a.total;
      out.innerHTML = `<h2>SIMULATED result <small class="muted">(what-if, not stored)</small></h2>
<div class="panel" style="text-align:center"><div style="font-size:2.4rem"><b>${fmt(t.score)}</b> ${esc(t.grade || '')} ${pill(t.status)}</div>
<div class="muted">Weighted ${fmt(t.weighted)} | Compound penalty ${esc(t.penalty)} | Change vs Day 1 ${fmt(t.delta_from_day1)}</div>
${t.capped ? '<div class="err" role="alert"><b>Bottleneck cap applied:</b> a division is below the red line, so the total cannot exceed Grade D.</div>' : ''}
${t.penalty ? '<div class="warn">Compound penalty: 3 or more divisions are not GREEN.</div>' : ''}</div>
<table><thead><tr><th>Division</th><th>Score</th><th>Status</th><th>Main deductions</th></tr></thead><tbody>${DIV_ORDER.map((k) => { const d = a.divisions[k]; return `<tr><td>${esc(DIV_NAMES[k])}</td><td>${fmt(d.score)} ${esc(d.grade || '')}</td><td>${pill(d.status)}</td><td>${(d.factors || []).map((f) => esc(f.label) + ' (-' + fmt(f.deduction) + ')').join('; ') || '--'}</td></tr>`; }).join('')}</tbody></table>
${(a.interaction_flags || []).length ? `<p class="muted">Interaction hypotheses: ${a.interaction_flags.map((f) => esc(f.pair.join(' + '))).join(', ')} (Hypothesis from HRP hazard descriptions)</p>` : ''}
<p class="muted">${esc(a.label)}</p>`;
    } catch (e) { if (!dead && my === seq) out.innerHTML = `<div class="err" role="alert"><b>Calculation failed.</b><p>${esc(e.message)}</p></div>`; }
  }
  const sched = () => { clearTimeout(timer); timer = setTimeout(calc, 100); };
  el.querySelectorAll('[data-k]').forEach((i) => {
    i.oninput = i.onchange = () => {
      const k = i.dataset.k;
      vals[k] = i.type === 'checkbox' ? (i.checked ? 1 : 0) : i.type === 'range' ? Number(i.value) : i.value;
      const v = el.querySelector(`[data-v="${k}"]`); if (v) v.textContent = vals[k];
      sched();
    };
  });
  el.querySelector('#rst').onclick = () => { for (const [, fs] of FIELDS) for (const f of fs) { const d = f[2] === 'bool' || f[2] === 'select' ? f[3] : f[5]; vals[f[0]] = d; const i = el.querySelector(`[data-k="${f[0]}"]`); if (i.type === 'checkbox') i.checked = !!d; else i.value = d; const v = el.querySelector(`[data-v="${f[0]}"]`); if (v) v.textContent = d; } calc(); };
  calc();
  return () => { dead = true; clearTimeout(timer); };
}
`

## File: frontend/js/pages/hud.js

`javascript
﻿import { get } from '../api.js';
import { esc, DIV_ORDER, DIV_NAMES, src, pill, fmt, loading, errorPanel, drawChart, breakdown } from '../ui.js';

export function render(root, opts = {}) {
  const hudMode = opts.mode === 'hud';
  const title = hudMode ? 'Flight Surgeon HUD' : 'Crew Health &amp; Mental Health Guard';
  let chart = null, dead = false, astro = null;

  async function load() {
    root.innerHTML = `<h1>${title}</h1>${loading('Loading crew assessments...')}`;
    try {
      const latest = (await get('/api/assessments/latest')).items || [];
      if (dead) return;
      if (!latest.length) { root.innerHTML = `<h1>${title}</h1><div class="empty"><b>No assessments yet.</b><br>Upload telemetry on Mission Control first.</div>`; return; }
      if (!astro || !latest.some((l) => l.astronaut_id === astro)) astro = latest[0].astronaut_id;
      const traj = (await get('/api/assessments?astronaut_id=' + encodeURIComponent(astro))).items || [];
      if (dead) return;
      draw(latest, traj.length ? traj : [latest.find((l) => l.astronaut_id === astro)]);
    } catch (e) { if (!dead) errorPanel(root, e, load); }
  }

  function draw(latest, traj) {
    const a = traj[traj.length - 1], t = a.total, dl = t.delta_from_day1;
    let h = `<div class="${hudMode ? 'hud' : ''}"><h1>${title}</h1><p class="sub">Readiness &amp; Condition Index &mdash; Illustrative screening metric, not a medical diagnosis. Defer to the flight surgeon and mission procedures.</p>
      <div class="row panel"><label>Astronaut <select id="astro">${latest.map((l) => `<option ${l.astronaut_id === astro ? 'selected' : ''}>${esc(l.astronaut_id)}</option>`).join('')}</select></label>
      <span>Day ${a.mission_day} &middot; scenario ${esc(a.scenario_label)}</span>${src(a.source)}<span class="muted">${esc(a.timestamp)}</span></div>
      <div class="panel"><div class="total"><div class="badge st-${esc(t.status)}"><div class="big">${fmt(t.score)}</div><div class="lt">Grade ${esc(t.grade)}</div>${pill(t.status)}</div>
      <div><div>Total Mission Grade ${src(a.source)}</div><div>Delta from Day 1: <b class="delta ${dl < 0 ? 'neg' : 'pos'}">${dl > 0 ? '+' : ''}${fmt(dl)}</b></div>
      ${t.capped ? '<span class="flag bad">Capped by bottleneck</span>' : ''}${t.penalty < 0 ? `<span class="flag warn">${fmt(t.penalty, 0)} compounding</span>` : ''}</div></div></div>
      <div class="panel"><h2>5-Division Breakdown</h2>${breakdown(a)}</div>
      <div class="panel"><h2>Contributing factors</h2><div class="grid g2">${DIV_ORDER.map((k) => { const d = a.divisions[k] || {}; const f = d.factors || [];
        return `<div><b>${esc(DIV_NAMES[k])}</b> ${pill(d.status || 'NO_DATA')}${f.length ? `<ul class="clean">${f.map((x) => `<li>${esc(x.label)}: ${esc(x.value)} <span class="delta neg">${fmt(x.deduction, 1)}</span></li>`).join('')}</ul>` : '<div class="muted">No deductions.</div>'}</div>`; }).join('')}</div></div>
      <div class="panel"><h2>Interaction watch (hypotheses)</h2>${(a.interaction_flags || []).length ? a.interaction_flags.map((f) => `<div><span class="flag warn">${esc(f.pair.map((p) => DIV_NAMES[p] || p).join(' + '))}</span> <span class="muted">${esc(f.label)}</span></div>`).join('') : '<span class="muted">No interaction flags. (Hypotheses from HRP hazard descriptions, not validated coefficients.)</span>'}</div>
      <div class="panel"><h2>Grade Trajectory Overlay</h2><div class="chartbox"><canvas id="ch" role="img" aria-label="Grade trajectory"></canvas></div></div></div>`;
    root.innerHTML = h;
    root.querySelector('#astro').onchange = (e) => { astro = e.target.value; load(); };
    chart = drawChart(root.querySelector('#ch'), traj, chart);
  }

  load();
  return () => { dead = true; if (chart) chart.destroy(); };
}
`

## File: frontend/js/pages/guards.js

`javascript
import { get } from '../api.js';
import { esc, src, pill, fmt, loading, errorPanel } from '../ui.js';

const TABS = [
  ['radiation', 'radiation-guard', 'Radiation'], ['mental_health', 'mental-health-guard', 'Mental Health'],
  ['gravity', 'gravity-guard', 'Gravity Health'], ['life_support', 'life-support-guard', 'Life Support'],
  ['earth_distance', 'earth-distance-guard', 'Earth Distance'],
];
const NOTE = 'Readiness & Condition Index - illustrative screening metric, not a medical diagnosis. Defer to the flight surgeon and mission procedures.';
const NOEXPOSE = 'Not exposed by the API (no deduction, or metric is not graded); no value is invented.';

// Each guard: metrics = [{label, codes:[factor codes], unit, note}], series = [{label, codes}] for trend (right axis).
const CFG = {
  radiation: { title: 'Radiation Guard', blurb: 'Cumulative dose against the 600 mSv career limit (illustrative).',
    metrics: [
      { label: 'Cumulative dose', codes: ['CUM_DOSE'], f: 'cum_dose_msv', unit: 'mSv', empty: 'No dose deduction recorded (dose 0 or missing).' },
      { label: 'Proton flux', codes: ['PROTON_FLUX'], f: 'proton_flux_pfu', unit: 'pfu', empty: 'Below the 10 pfu threshold (or not reported); value not exposed.' },
      { label: 'Solar flare', codes: ['FLARE_ACTIVE'], f: 'flare_active', unit: '', empty: 'No active flare flagged.', bool: true }],
    series: [{ label: 'Cumulative dose (mSv)', codes: [], f: 'cum_dose_msv' }, { label: 'Proton flux (pfu)', codes: [], f: 'proton_flux_pfu' }],
    foot: 'Dose is from dose records, never converted from NOAA flux.' },
  mental_health: { title: 'Mental Health Guard', blurb: 'Sleep, HRV vs baseline, fatigue and stress.',
    metrics: [
      { label: 'Sleep', codes: ['SLEEP_SEVERE', 'SLEEP_LOW'], f: 'sleep_h', unit: 'h', empty: 'Sleep at or above 6 h (value not exposed).' },
      { label: 'HRV drop vs baseline', codes: ['HRV_DROP'], f: 'hrv_rmssd_ms', f2: 'hrv_baseline_ms', unit: 'ms', empty: 'No HRV drop below baseline (raw HRV and baseline not exposed).' },
      { label: 'Fatigue (0-10)', codes: ['FATIGUE'], f: 'fatigue', unit: '', empty: 'At or below 5 (value not exposed).' },
      { label: 'Stress (0-10)', codes: ['STRESS'], f: 'stress', unit: '', empty: 'At or below 5 (value not exposed).' }],
    series: [{ label: 'Sleep (h)', codes: [], f: 'sleep_h' }, { label: 'HRV RMSSD (ms)', codes: [], f: 'hrv_rmssd_ms' }, { label: 'HRV baseline (ms)', codes: [], f: 'hrv_baseline_ms' },
      { label: 'Fatigue', codes: [], f: 'fatigue' }, { label: 'Stress', codes: [], f: 'stress' }],
    foot: 'HRV baseline is a personal baseline; the API exposes only the % drop when it deducts.' },
  gravity: { title: 'Gravity Health Guard', blurb: 'Exercise-loading index against target, and vestibular balance score.',
    metrics: [
      { label: 'Exercise-loading index / target (ratio, deducts below 0.80)', codes: ['LOADING_LOW'], f: 'loading_index', f2: 'loading_target', unit: '', empty: 'Loading at or above 80% of target (ratio not exposed).' },
      { label: 'Balance score (0-100, deducts below 85)', codes: ['BALANCE_LOW'], f: 'balance_score', unit: '', empty: 'Balance at or above 85 (value not exposed).' }],
    series: [{ label: 'Loading index', codes: [], f: 'loading_index' }, { label: 'Loading target', codes: [], f: 'loading_target' }, { label: 'Balance score', codes: [], f: 'balance_score' }],
    foot: 'Tracks exercise loading as a countermeasure indicator only; this is not a bone-health measurement.' },
  life_support: { title: 'Life Support Guard', blurb: 'Cabin O2, CO2 (5000 ppm line), pressure, scrubber state.',
    metrics: [
      { label: 'CO2 (limit 5000 ppm)', codes: ['CO2_HIGH'], f: 'cabin_co2_ppm', unit: 'ppm', empty: 'At or below 5000 ppm (value not exposed).' },
      { label: 'O2 (19.5-23.5 %)', codes: ['O2_OUT_OF_RANGE'], f: 'cabin_o2_pct', unit: '%', empty: 'Within range (value not exposed).' },
      { label: 'Pressure (97-103 kPa)', codes: ['PRESSURE_OUT_OF_RANGE'], f: 'cabin_pressure_kpa', unit: 'kPa', empty: 'Within range (value not exposed).' },
      { label: 'Scrubber state', codes: ['SCRUBBER_DEGRADED', 'SCRUBBER_OFFLINE'], f: 'scrubber_state', unit: '', empty: 'Nominal (or not reported).' },
      { label: 'Temperature', codes: [], f: 'cabin_temp_c', unit: 'C', empty: NOEXPOSE + ' Not part of the score.' },
      { label: 'Humidity', codes: [], f: 'cabin_humidity_pct', unit: '%', empty: NOEXPOSE + ' Not part of the score.' }],
    series: [{ label: 'CO2 (ppm)', codes: [], f: 'cabin_co2_ppm', limit: 5000 }, { label: 'O2 (%)', codes: [], f: 'cabin_o2_pct' }, { label: 'Pressure (kPa)', codes: [], f: 'cabin_pressure_kpa' }, { label: 'Temp (C)', codes: [], f: 'cabin_temp_c' }, { label: 'Humidity (%)', codes: [], f: 'cabin_humidity_pct' }],
    foot: 'Raw values come from stored telemetry; temperature and humidity are informational and not part of the score.' },
  earth_distance: { title: 'Earth Distance Guard', blurb: 'Communication latency tier and open medical flags.',
    metrics: [
      { label: 'Latency (s)', codes: ['LATENCY_TIER2', 'LATENCY_TIER3'], f: 'latency_s', unit: 's', empty: 'Tier 1, or no other division degraded (latency only appears when it deducts).' },
      { label: 'Open medical flags', codes: ['OPEN_MEDICAL_FLAGS'], f: 'open_medical_flags', unit: '', empty: 'None open (or not reported).' }],
    series: [{ label: 'Latency (s)', codes: [], f: 'latency_s' }, { label: 'Open flags', codes: [], f: 'open_medical_flags' }],
    foot: 'Tier 1 < 2 s, tier 2 2-60 s, tier 3 > 60 s.' },
};
const COLORS = ['#f472b6', '#facc15', '#60a5fa', '#34d399', '#fb923c', '#a78bfa'];

const factorOf = (div, codes) => ((div && div.factors) || []).find((f) => codes.includes(f.code));
const valueOf = (div, codes) => { const f = factorOf(div, codes); return f ? f.value : null; };

const STALE_MS = 48 * 3600 * 1000;
// latest non-null raw value for a field, flagged stale if its row is >48 h older than the newest row
function rawLatest(raw, f) {
  if (!raw.length || !f) return null;
  const newest = Date.parse(raw[raw.length - 1].timestamp);
  for (let i = raw.length - 1; i >= 0; i--) {
    const v = raw[i][f];
    if (v != null && v !== '') return { v, row: raw[i], stale: newest - Date.parse(raw[i].timestamp) > STALE_MS };
  }
  return null;
}

function tabs(key) {
  return `<nav class="gtabs" aria-label="Guards">${TABS.map(([k, id, t]) => `<a href="#/${id}" ${k === key ? 'aria-current="page"' : ''}>${esc(t)}</a>`).join('')}</nav>`;
}

function csvDose(traj) {
  const rows = ['mission_day,timestamp,cum_dose_msv,source'];
  for (const a of traj) { const v = valueOf(a.divisions.radiation, ['CUM_DOSE']); rows.push([a.mission_day, a.timestamp, v == null ? '' : v, a.source].join(',')); }
  return rows.join('\n');
}

function triage(a) {
  const ed = a.divisions.earth_distance || {};
  const lat = valueOf(ed, ['LATENCY_TIER2', 'LATENCY_TIER3']);
  const tier = ed.factors && ed.factors.some((f) => f.code === 'LATENCY_TIER3') ? 3 : ed.factors && ed.factors.some((f) => f.code === 'LATENCY_TIER2') ? 2 : null;
  const open = valueOf(ed, ['OPEN_MEDICAL_FLAGS']) || 0;
  const bad = Object.values(a.divisions).filter((d) => d.key !== 'earth_distance' && (d.status === 'YELLOW' || d.status === 'RED'));
  const steps = [];
  if (bad.some((d) => d.status === 'RED')) steps.push('At least one division is RED: treat as urgent. Alert the crew medical officer and attempt contact with the flight surgeon now.');
  else if (bad.length) steps.push('Degraded division(s): ' + bad.map((d) => d.name).join(', ') + '. Review the guard tab for each and log observations.');
  else steps.push('No other division is degraded. Continue routine monitoring.');
  if (tier === 3) steps.push('Tier 3 delay (>60 s): real-time consultation is not possible. Send a structured written report and follow the pre-agreed mission procedures while awaiting reply.');
  else if (tier === 2) steps.push('Tier 2 delay (2-60 s): conversation is possible but delayed. Send a concise report and wait for acknowledgement between messages.');
  else steps.push('Latency tier is tier 1 or not flagged: normal two-way contact expected.');
  if (open > 0) steps.push(open + ' open medical flag(s): review and report each to the flight surgeon.');
  steps.push('Record symptoms, time of onset and measurements, and keep the log ready to transmit.');
  steps.push('Follow the onboard medical checklists. This tool gives no medication or dosage guidance. All treatment decisions belong to the flight surgeon.');
  return { steps, tier, lat };
}

export async function renderGuard(root, key) {
  const cfg = CFG[key];
  let chart = null, dead = false, astro = null, raw = [];
  async function load() {
    root.innerHTML = `<h1>${esc(cfg.title)}</h1>${tabs(key)}${loading('Loading assessments...')}`;
    try {
      const latest = (await get('/api/assessments/latest')).items || [];
      if (dead) return;
      if (!latest.length) { root.innerHTML = `<h1>${esc(cfg.title)}</h1>${tabs(key)}<div class="empty"><b>No assessments yet.</b><br>Upload telemetry on Mission Control first.</div>`; return; }
      if (!astro || !latest.some((l) => l.astronaut_id === astro)) astro = latest[0].astronaut_id;
      const traj = (await get('/api/assessments?astronaut_id=' + encodeURIComponent(astro))).items || [];
      if (dead) return;
      try { raw = (await get('/api/telemetry?astronaut_id=' + encodeURIComponent(astro))).items || []; } catch (e) { raw = []; }
      if (dead) return;
      draw(latest, traj.length ? traj : [latest.find((l) => l.astronaut_id === astro)]);
    } catch (e) { if (!dead) errorPanel(root, e, load); }
  }
  function draw(latest, traj) {
    const a = traj[traj.length - 1], d = a.divisions[key];
    if (!d) { root.innerHTML = `<h1>${esc(cfg.title)}</h1>${tabs(key)}<div class="empty">This division is missing from the assessment.</div>`; return; }
    const noData = d.status === 'NO_DATA';
    const rows = cfg.metrics.map((m) => {
      const f = factorOf(d, m.codes);
      const rl = rawLatest(raw, m.f), rl2 = m.f2 ? rawLatest(raw, m.f2) : null;
      let val;
      if (rl) {
        const shown = m.bool ? (rl.v ? 'Active' : 'Inactive') : esc(typeof rl.v === 'number' ? fmt(rl.v, 2) : rl.v) + (m.unit ? ' ' + esc(m.unit) : '') + (rl2 ? ' (baseline ' + esc(fmt(rl2.v, 1)) + ')' : '');
        val = '<b>' + shown + '</b> ' + src(rl.row.source) + (rl.stale ? ' <span class="flag warn" title="Health record more than 48 h older than the latest row">stale &gt;48 h (day ' + esc(rl.row.mission_day) + ')</span>' : '');
      } else if (noData) val = '<span class="muted">NO_DATA - required inputs missing</span>';
      else if (f) val = `<b>${m.bool ? 'Active' : esc(f.value) + (m.unit ? ' ' + esc(m.unit) : '')}</b>`;
      else val = `<span class="muted">${esc(m.empty)}</span>`;
      return `<tr><td>${esc(m.label)}</td><td>${val}</td><td>${f ? `<span class="delta neg">-${fmt(f.deduction, 1)}</span>` : '--'}</td></tr>`;
    }).join('');
    const ftab = (d.factors || []).length
      ? `<table><thead><tr><th>Code</th><th>Factor</th><th>Value</th><th>Deduction</th></tr></thead><tbody>${d.factors.map((f) => `<tr><td>${esc(f.code)}</td><td>${esc(f.label)}</td><td>${esc(f.value)}</td><td class="delta neg">-${fmt(f.deduction, 2)}</td></tr>`).join('')}</tbody></table>`
      : '<div class="muted">No deductions at this reading.</div>';
    let extra = '';
    if (key === 'radiation') {
      const dose = valueOf(d, ['CUM_DOSE']) || 0, pct = Math.min(100, dose / 6);
      const fs = d.factors || [];
      extra = `<div class="panel"><h2>Cumulative dose vs 600 mSv limit</h2>
        <div class="bar ${pct >= 80 ? 'RED' : pct >= 50 ? 'YELLOW' : 'GREEN'}" role="img" aria-label="Dose ${fmt(dose)} of 600 mSv"><i style="width:${pct}%"></i></div>
        <p>${fmt(dose)} mSv of 600 mSv (${fmt(pct)}%) ${src(a.source)}</p>
        <p>Proton factor: ${fs.some((f) => f.code === 'PROTON_FLUX') ? '<span class="flag bad">Proton flux at or above 10 pfu</span>' : '<span class="muted">not triggered</span>'}
        Flare factor: ${fs.some((f) => f.code === 'FLARE_ACTIVE') ? '<span class="flag warn">Flare active</span>' : '<span class="muted">not triggered</span>'}</p>
        <button id="csv">Export dose series (CSV)</button></div>`;
    }
    if (key === 'earth_distance') {
      const t = triage(a);
      extra = `<div class="panel"><h2>Latency tier</h2><p>Tier 1 &lt; 2 s &middot; Tier 2 2-60 s &middot; Tier 3 &gt; 60 s. Current: <b>${t.tier ? 'Tier ' + t.tier + ' (' + fmt(t.lat, 0) + ' s)' : 'tier not exposed (tier 1, or no other division degraded)'}</b> ${src(a.source)}</p></div>
        <div class="panel"><h2>Offline triage guide</h2><p class="muted">Rule-based checklist for when Earth contact is delayed. No medications or dosages.</p>
        <button id="tri" class="primary">Launch offline triage</button><div id="triout" hidden></div></div>`;
    }
    root.innerHTML = `<h1>${esc(cfg.title)}</h1>${tabs(key)}<p class="sub">${esc(cfg.blurb)} ${esc(NOTE)}</p>
      <div class="row panel"><label>Astronaut <select id="astro">${latest.map((l) => `<option ${l.astronaut_id === astro ? 'selected' : ''}>${esc(l.astronaut_id)}</option>`).join('')}</select></label>
        <span>Day ${esc(a.mission_day)} &middot; ${esc(a.scenario_label)}</span>${src(a.source)}</div>
      <div class="panel"><div class="total"><div class="badge st-${esc(d.status)}"><div class="big">${fmt(d.score)}</div><div class="lt">${esc(d.grade || '--')}</div>${pill(d.status)}</div>
        <div><div>${esc(d.name)} sub-score ${src(a.source)}</div><div class="muted">Division sub-score (0-100), letter and status.</div></div></div></div>
      ${extra}
      <div class="panel"><h2>Metrics</h2><table><thead><tr><th>Metric</th><th>Value</th><th>Deduction</th></tr></thead><tbody>${rows}</tbody></table><p class="muted">${esc(cfg.foot)}</p></div>
      <div class="panel"><h2>Factors table</h2>${ftab}</div>
      <div class="panel"><h2>Trend</h2><div class="chartbox"><canvas id="ch" role="img" aria-label="${esc(cfg.title)} trend"></canvas></div></div>`;
    root.querySelector('#astro').onchange = (e) => { astro = e.target.value; load(); };
    const csv = root.querySelector('#csv');
    if (csv) csv.onclick = () => { const u = URL.createObjectURL(new Blob([csvDose(traj)], { type: 'text/csv' })); const l = document.createElement('a'); l.href = u; l.download = 'dose_series.csv'; l.click(); URL.revokeObjectURL(u); };
    const tri = root.querySelector('#tri');
    if (tri) tri.onclick = () => { const o = root.querySelector('#triout'); o.hidden = !o.hidden; o.innerHTML = '<ol>' + triage(a).steps.map((s) => `<li>${esc(s)}</li>`).join('') + '</ol>'; };
    drawTrend(traj);
  }
  function drawTrend(traj) {
    const canvas = root.querySelector('#ch');
    if (chart) chart.destroy();
    if (!window.Chart) { canvas.replaceWith(Object.assign(document.createElement('p'), { className: 'muted', textContent: 'Chart library failed to load.' })); return; }
    const rawByTs = {}; raw.forEach((r) => { rawByTs[r.timestamp] = r; });
    const ds = [{ label: 'Division score', data: traj.map((a) => (a.divisions[key] ? a.divisions[key].score : null)), borderColor: '#22d3ee', borderWidth: 3, tension: .2, pointRadius: 2, yAxisID: 'y' }];
    cfg.series.forEach((s, i) => {
      ds.push({ label: s.label, data: traj.map((a) => { const r = rawByTs[a.timestamp]; return r && typeof r[s.f] === 'number' ? r[s.f] : null; }), borderColor: COLORS[i % COLORS.length], borderWidth: 1.5, pointRadius: 2, tension: .2, spanGaps: false, yAxisID: 'y1' });
      if (s.limit) ds.push({ label: s.label.split(' ')[0] + ' limit', data: traj.map(() => s.limit), borderColor: '#ff4d4d', borderDash: [6, 4], pointRadius: 0, yAxisID: 'y1' });
    });
    Chart.defaults.color = '#9db3d6';
    chart = new Chart(canvas, { type: 'line', data: { labels: traj.map((a) => a.mission_day), datasets: ds }, options: { responsive: true, maintainAspectRatio: false, animation: false,
      scales: { y: { min: 0, max: 100, title: { display: true, text: 'Score' }, grid: { color: '#1e3358' } }, y1: { position: 'right', title: { display: true, text: 'Raw value (stored telemetry)' }, grid: { drawOnChartArea: false } }, x: { title: { display: true, text: 'mission_day' }, grid: { color: '#1e3358' } } },
      plugins: { legend: { labels: { color: '#e8f1ff' } } } } });
  }
  load();
  return () => { dead = true; if (chart) chart.destroy(); };
}

export function render(root, opts = {}) { return renderGuard(root, opts.key || 'radiation'); }
`

## File: frontend/js/pages/ai-risk.js

`javascript
﻿import { get } from '../api.js';
import { esc, DIV_ORDER, DIV_NAMES, pill, fmt, src, loading, errorPanel } from '../ui.js';

export async function render(el) {
  async function load() {
    el.innerHTML = `<h1>AI Risk Analysis</h1>${loading('Loading assessments...')}`;
    try {
      const items = (await get('/api/assessments/latest')).items || [];
      let h = `<h1>AI Risk Analysis</h1><p class="sub">Explainable rule-and-statistics engine. Early-warning screening, not a diagnosis. Defer to the flight surgeon.</p>`;
      if (!items.length) { el.innerHTML = h + `<div class="empty"><b>No assessments yet.</b> Upload telemetry first.</div>`; return; }
      h += `<div class="panel"><table><thead><tr><th>Astronaut</th><th>Day</th><th>Total</th>${DIV_ORDER.map((k) => `<th>${esc(DIV_NAMES[k])}</th>`).join('')}<th>Source</th></tr></thead><tbody>${items.map((a) => `<tr>
        <td>${esc(a.astronaut_id)}</td><td>${esc(a.mission_day)}</td><td><b>${fmt(a.total.score)}</b> ${esc(a.total.grade || '')} ${pill(a.total.status)}${a.total.capped ? ' <span class="muted">(capped)</span>' : ''}</td>
        ${DIV_ORDER.map((k) => { const d = a.divisions[k] || {}; return `<td>${fmt(d.score)} ${pill(d.status || 'NO_DATA')}</td>`; }).join('')}<td>${src(a.source)}</td></tr>`).join('')}</tbody></table></div>`;
      for (const a of items) {
        const rows = DIV_ORDER.flatMap((k) => ((a.divisions[k] || {}).factors || []).map((f) => `<li><b>${esc(DIV_NAMES[k])}</b>: ${esc(f.label)} (value ${esc(f.value)}) lowered the score by ${fmt(f.deduction, 1)} points.</li>`));
        const fl = a.interaction_flags || [];
        h += `<div class="panel"><h3>${esc(a.astronaut_id)} &mdash; why this score</h3>
          ${rows.length ? `<ul>${rows.join('')}</ul>` : '<p class="muted">No deduction factors: all divisions nominal.</p>'}
          <h4>Interaction watch <span class="muted">(hypotheses)</span></h4>
          ${fl.length ? `<ul>${fl.map((f) => `<li>${esc((f.pair || []).map((p) => DIV_NAMES[p] || p).join(' + '))}: <i>${esc(f.label)}</i></li>`).join('')}</ul>` : '<p class="muted">No interaction flags.</p>'}</div>`;
      }
      el.innerHTML = h;
    } catch (e) { errorPanel(el, e, load); }
  }
  await load();
}
`

## File: frontend/js/pages/alerts.js

`javascript
﻿import { get } from '../api.js';
import { esc, loading, errorPanel } from '../ui.js';

const SEV = ['critical', 'warning', 'info'];

export async function render(el) {
  let filter = 'all';
  async function load() {
    el.innerHTML = `<h1>Alerts Centre</h1>${loading('Loading alerts...')}`;
    try {
      const [al, sw] = await Promise.all([get('/api/alerts'), get('/api/spaceweather').catch((e) => ({ status: 'FAILED', error: e.message }))]);
      draw(al.items || [], sw);
    } catch (e) { errorPanel(el, e, load); }
  }
  function draw(items, sw) {
    const seen = new Set();
    const uniq = items.filter((a) => { const k = [a.astronaut_id, a.code, a.day].join('|'); if (seen.has(k)) return false; seen.add(k); return true; });
    const shown = uniq.filter((a) => filter === 'all' || a.severity === filter);
    const p = sw && sw.data && sw.data.proton_flux;
    let h = `<h1>Alerts Centre</h1><p class="sub">De-duplicated rule alerts. Screening aids, not diagnoses.</p>`;
    if (p && p.sep_active) h += `<div class="err" role="alert"><b>SHELTER BANNER: NOAA S1 threshold reached</b> (proton flux ${esc(p.value)} pfu, &ge;10 pfu at &ge;10 MeV). Follow mission shelter procedures.</div>`;
    else if (sw && sw.status === 'FAILED') h += `<div class="warn">Space-weather status unavailable (${esc(sw.error)}); shelter banner cannot be evaluated.</div>`;
    h += `<div class="row panel">${['all', ...SEV].map((s) => `<button data-f="${s}" class="${filter === s ? 'primary' : ''}">${s}${s === 'all' ? ' (' + uniq.length + ')' : ' (' + uniq.filter((a) => a.severity === s).length + ')'}</button>`).join('')}</div>`;
    h += shown.length ? `<div class="panel"><table><thead><tr><th>Severity</th><th>Astronaut</th><th>Day</th><th>Code</th><th>Message</th><th>Created</th></tr></thead><tbody>${shown.map((a) => `<tr><td><span class="pill ${a.severity === 'critical' ? 'RED' : a.severity === 'warning' ? 'YELLOW' : 'GREEN'}">${esc(a.severity)}</span></td><td>${esc(a.astronaut_id)}</td><td>${esc(a.day)}</td><td>${esc(a.code)}</td><td>${esc(a.message)}</td><td>${esc(a.created_at)}</td></tr>`).join('')}</tbody></table></div>`
      : `<div class="empty"><b>No alerts${filter === 'all' ? '' : ' at severity ' + esc(filter)}.</b></div>`;
    el.innerHTML = h;
    el.querySelectorAll('[data-f]').forEach((b) => { b.onclick = () => { filter = b.dataset.f; draw(items, sw); }; });
  }
  await load();
}
`

## File: frontend/js/pages/spaceweather.js

`javascript
﻿import { get, postJson } from '../api.js';
import { esc, fmt, loading, errorPanel } from '../ui.js';

const SIM = {
  S1: { label: 'S1 (minor)', flux: 10, note: 'Rehearsal at the NOAA S1 threshold (10 pfu).' },
  S3: { label: 'S3 (strong)', flux: 1000, note: 'Rehearsal at the NOAA S3 threshold (1000 pfu).' },
};
const age = (s) => s == null ? '--' : s < 90 ? Math.round(s) + ' s' : Math.round(s / 60) + ' min';

export async function render(el) {
  let sim = null;
  async function load(refresh) {
    el.innerHTML = `<h1>Space Weather</h1>${loading('Fetching NOAA SWPC data...')}`;
    try {
      const sw = refresh ? await postJson('/api/spaceweather/refresh', {}) : await get('/api/spaceweather');
      draw(sw);
    } catch (e) { errorPanel(el, e, () => load(true)); }
  }
  function draw(sw) {
    const d = sw.data, st = sw.status;
    const badge = `<span class="pill ${st === 'LIVE' ? 'GREEN' : st === 'CACHED' ? 'YELLOW' : 'RED'}">${esc(st)}</span>`;
    let h = `<h1>Space Weather</h1><p class="sub">NOAA SWPC GOES observations. No forecasting of solar events; flux is never converted to astronaut dose.</p>
    <div class="panel row">${badge}
      <span>Fetched at: <b>${esc(sw.fetched_at || 'never')}</b></span><span>Age: <b>${esc(age(sw.age_s))}</b></span>
      ${sw.stale ? '<span class="pill RED" title="Older than 30 minutes">STALE (&gt;30 min)</span>' : ''}
      <button class="primary" id="sw-retry">${st === 'FAILED' ? 'Retry' : 'Refresh'}</button></div>`;
    if (sw.error) h += `<div class="err" role="alert"><b>${st === 'FAILED' ? 'NOAA data unavailable.' : 'Last refresh failed; showing cached values.'}</b><p>Reason: ${esc(sw.error)}</p></div>`;
    if (!d) h += `<div class="empty"><b>No space-weather data.</b> Nothing is shown rather than inventing values.</div>`;
    else {
      const p = d.proton_flux || {}, x = d.xray_flux || {}, k = d.kp || {}, sc = d.scales || {};
      if (p.sep_active) h += `<div class="err" role="alert"><b>SHELTER ADVISORY: NOAA S1 threshold reached</b> &mdash; ${esc(p.sep_label || '>=10 pfu at >=10 MeV')}. Follow mission shelter procedures.</div>`;
      h += `<div class="grid"><div class="panel"><h3>Proton flux (&ge;10 MeV)</h3><div class="big">${fmt(p.value, 2)} <small>${esc(p.unit || '')}</small></div><div class="muted">Observed ${esc(p.observed_at || '--')} &middot; ${esc(p.satellite || '')}</div></div>
      <div class="panel"><h3>X-ray flux (0.1-0.8 nm)</h3><div class="big">${x.value == null ? '--' : Number(x.value).toExponential(2)} <small>${esc(x.unit || '')}</small></div><div class="muted">Observed ${esc(x.observed_at || '--')}</div></div>
      <div class="panel"><h3>Planetary Kp</h3><div class="big">${fmt(k.value, 2)}</div><div class="muted">Observed ${esc(k.observed_at || '--')}</div></div></div>
      <div class="panel"><h3>NOAA scales (current)</h3><p>${['R', 'S', 'G'].map((n) => { const v = sc[n] || {}; return `<b>${n}${esc(v.scale ?? '--')}</b> ${esc(v.text || '')}`; }).join(' &nbsp;|&nbsp; ')}</p><p class="muted">Observed ${esc(sc.observed_at || '--')}</p></div>`;
    }
    h += `<div class="panel" id="sim"><h3>Storm rehearsal <span class="src SIMULATED">SIMULATED</span></h3>
      <p class="muted">Training scenario only. Not live data, not a forecast; separate from the values above.</p>
      <div class="row"><button id="sim-S1">Rehearse S1</button><button id="sim-S3">Rehearse S3</button><button id="sim-off">Clear</button></div>`;
    if (sim) h += `<div class="warn" role="status"><span class="src SIMULATED">SIMULATED</span> ${esc(SIM[sim].label)}: proton flux ${SIM[sim].flux} pfu. ${esc(SIM[sim].note)} Rehearse shelter procedures; this is not a real event.</div>`;
    h += `</div>`;
    el.innerHTML = h;
    el.querySelector('#sw-retry').onclick = () => load(true);
    for (const k of ['S1', 'S3']) el.querySelector('#sim-' + k).onclick = () => { sim = k; draw(sw); };
    el.querySelector('#sim-off').onclick = () => { sim = null; draw(sw); };
  }
  await load(false);
}
`

## File: frontend/js/pages/reports.js

`javascript
﻿import { get } from '../api.js';
import { esc, fmt, pill, loading, errorPanel, DIV_ORDER, DIV_NAMES, breakdown } from '../ui.js';

const PRINT_CSS = `@media print{.sidebar,.mobilebar,.noprint,#footer{display:none!important}body,.shell,.main,.panel{background:#fff!important;color:#000!important}.shell{display:block!important}.main{margin:0!important;padding:0!important}.panel{border:1px solid #999!important}table{color:#000!important}.pill,.src{border:1px solid #000;color:#000!important;background:#fff!important}.printonly{display:block!important}}.printonly{display:none}`;

export async function render(el) {
  if (!document.getElementById('rep-print')) { const s = document.createElement('style'); s.id = 'rep-print'; s.textContent = PRINT_CSS; document.head.appendChild(s); }
  async function load() {
    el.innerHTML = `<h1>Reports &amp; Analytics</h1>${loading()}`;
    try {
      const [latest, crew] = await Promise.all([get('/api/assessments/latest'), get('/api/crew')]);
      draw(latest.items || [], crew.items || []);
    } catch (e) { errorPanel(el, e, load); }
  }
  function draw(items, crew) {
    const names = Object.fromEntries(crew.map((c) => [c.astronaut_id, c.name]));
    let h = `<h1>Reports &amp; Analytics</h1><p class="sub">Exports of stored assessments. Screening aids only.</p>
<div class="panel noprint row"><label>Astronaut <select id="aid"><option value="">All</option>${items.map((a) => `<option>${esc(a.astronaut_id)}</option>`).join('')}</select></label>
<a class="btn primary" id="csv" href="/api/reports/assessments.csv" download>Download assessments CSV</a>
<button id="pdf" class="primary">Print / Save as PDF</button></div>
<div class="printonly"><h2>ORBITCARE 5X Crew Health Report</h2><p>Generated ${esc(new Date().toISOString())}</p></div>`;
    if (!items.length) h += `<div class="empty"><b>No assessments yet.</b><p>Upload telemetry on Mission Control or ingest data first; nothing is fabricated.</p></div>`;
    for (const a of items) {
      const t = a.total;
      h += `<div class="panel"><h2>${esc(names[a.astronaut_id] || a.astronaut_id)} <small class="muted">${esc(a.astronaut_id)} | day ${esc(a.mission_day)}</small></h2>
<p><b>Total ${fmt(t.score)} ${esc(t.grade || '')}</b> ${pill(t.status)} | Change vs Day 1 ${fmt(t.delta_from_day1)}${t.capped ? ' | <b>Bottleneck cap applied</b>' : ''}${t.penalty ? ' | Compound penalty ' + esc(t.penalty) : ''}</p>${breakdown(a)}
<table><thead><tr><th>Division</th><th>Deductions</th></tr></thead><tbody>${DIV_ORDER.map((k) => `<tr><td>${esc(DIV_NAMES[k])}</td><td>${(a.divisions[k].factors || []).map((f) => esc(f.label) + ' (-' + fmt(f.deduction) + ')').join('; ') || '--'}</td></tr>`).join('')}</tbody></table></div>`;
    }
    h += `<div class="panel"><b>Not a medical device.</b> ORBITCARE 5X is not a medical device or diagnostic system. This report contains an illustrative screening metric, not a medical diagnosis, and does not replace clinical judgement by a flight surgeon. Demo data is SIMULATED.</div>`;
    el.innerHTML = h;
    const sel = el.querySelector('#aid'), csv = el.querySelector('#csv');
    if (sel) sel.onchange = () => { csv.href = '/api/reports/assessments.csv' + (sel.value ? '?astronaut_id=' + encodeURIComponent(sel.value) : ''); };
    el.querySelector('#pdf').onclick = () => window.print();
  }
  await load();
}
`

## File: frontend/js/pages/settings.js

`javascript
﻿import { get, api, postFile } from '../api.js';
import { esc, loading, errorPanel } from '../ui.js';

const W_KEYS = ['radiation', 'life_support', 'mental_health', 'gravity', 'earth_distance'];

export async function render(el) {
  async function load() {
    el.innerHTML = `<h1>Settings</h1>${loading()}`;
    try { draw(await get('/api/settings')); } catch (e) { errorPanel(el, e, load); }
  }
  function draw(s) {
    const m = s.mission;
    el.innerHTML = `<h1>Settings</h1><p class="sub">Changes apply to assessments computed after saving; existing assessments are not recalculated.</p><div id="msg" role="status"></div>
<form class="panel" id="wf"><h2>Grading weights</h2><div class="row">${W_KEYS.map((k) => `<label>${esc(k)} <input type="number" step="0.01" min="0" max="1" name="${k}" value="${s.weights[k]}" style="width:80px"></label>`).join('')}</div><p>Sum: <b id="wsum"></b> (must be 1.00)</p><button class="primary" type="submit">Save weights</button></form>
<form class="panel" id="mf"><h2>Mission</h2><div class="row"><label>Name <input name="name" value="${esc(m.name)}"></label><label>Start (ISO UTC) <input name="start" value="${esc(m.start)}"></label><label>Planned days <input type="number" min="1" name="planned_days" value="${esc(m.planned_days)}" style="width:80px"></label></div><button class="primary" type="submit">Save mission</button></form>
<form class="panel" id="tf"><h2>Thresholds</h2><details><summary>Show all grading thresholds</summary>${Object.entries(s.thresholds).map(([g, d]) => `<fieldset style="border:1px solid var(--line);border-radius:8px;margin:8px 0"><legend>${esc(g)}</legend><div class="row">${Object.entries(d).map(([k, v]) => `<label>${esc(k)} <input type="number" step="any" data-g="${esc(g)}" data-k="${esc(k)}" value="${v}" style="width:90px"></label>`).join('')}</div></fieldset>`).join('')}</details><button class="primary" type="submit">Save thresholds</button></form>
<div class="panel"><h2>Backup &amp; restore</h2><div class="row"><a class="btn" href="/api/backup" download>Download backup JSON</a><label>Restore from backup <input type="file" id="rf" accept=".json,application/json"></label></div></div>
<div class="panel"><h2>Reset demo data</h2><p class="muted">Deletes all telemetry, assessments, alerts and crew. Settings are kept.</p><button id="reset" style="border-color:var(--red)">Reset demo data</button></div>`;
    const msg = (t, bad) => { el.querySelector('#msg').innerHTML = `<div class="${bad ? 'err' : 'warn'}" ${bad ? 'role="alert"' : ''}>${esc(t)}</div>`; };
    const put = async (body, label) => { try { await api('/api/settings', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }); msg(label + ' saved.'); } catch (e) { msg(e.message, true); } };
    const wf = el.querySelector('#wf');
    const sum = () => { const t = W_KEYS.reduce((a, k) => a + Number(wf[k].value || 0), 0); el.querySelector('#wsum').textContent = t.toFixed(2); };
    wf.oninput = sum; sum();
    wf.onsubmit = (e) => { e.preventDefault(); const w = {}; W_KEYS.forEach((k) => { w[k] = Number(wf[k].value); }); put({ weights: w }, 'Weights'); };
    const mf = el.querySelector('#mf');
    mf.onsubmit = (e) => { e.preventDefault(); put({ mission: { name: mf.name.value, start: mf.start.value, planned_days: Number(mf.planned_days.value) } }, 'Mission'); };
    el.querySelector('#tf').onsubmit = (e) => { e.preventDefault(); const t = {}; el.querySelectorAll('[data-g]').forEach((i) => { (t[i.dataset.g] ||= {})[i.dataset.k] = Number(i.value); }); put({ thresholds: t }, 'Thresholds'); };
    el.querySelector('#rf').onchange = async (e) => {
      const f = e.target.files[0]; if (!f) return;
      if (!window.confirm('Restore will REPLACE all current data with the backup. Continue?')) { e.target.value = ''; return; }
      try { const body = JSON.parse(await f.text()); const r = await api('/api/restore', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }); msg('Restored: ' + JSON.stringify(r.counts)); load(); } catch (err) { msg('Restore failed: ' + err.message, true); }
    };
    el.querySelector('#reset').onclick = async () => {
      if (!window.confirm('Delete ALL demo telemetry, assessments and alerts? This cannot be undone.')) return;
      try { const r = await api('/api/telemetry', { method: 'DELETE' }); msg('Demo data reset: ' + JSON.stringify(r.deleted)); } catch (err) { msg(err.message, true); }
    };
  }
  await load();
}
`
