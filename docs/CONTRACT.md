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
