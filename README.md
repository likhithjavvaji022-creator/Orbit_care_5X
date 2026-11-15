# ORBITCARE 5X

**Protecting Astronauts. Predicting Risks. Powering the Future of Space Exploration.**

ORBITCARE 5X is a web-based onboard decision-support prototype that brings NASA's five Human Research Program hazards into one place: Space Radiation, Distance From Earth, Gravity Fields, Closed Ecosystems, and Isolation & Stress. It grades each hazard division on a 0–100 scale, derives a Total Mission Grade, and shows the result on a Mission Control dashboard and a Flight Surgeon HUD.

Built for the NASA Space Apps Challenge 2026.

> The UI calls all outputs "early-warning screening". The tagline keeps the word "Predicting" as written in the project plan; the product makes no forecasting claims.

## Disclaimer

- ORBITCARE 5X is **not a medical device or diagnostic system**.
- **Readiness & Condition Index — Illustrative screening metric, not a medical diagnosis.**
- All crew data is **SIMULATED**. The people are **fictional**.
- Thresholds and deduction coefficients are illustrative defaults with source notes (see `docs/ASSUMPTIONS.md`). They are not validated science.
- Hazard interaction rules are hypotheses drawn from HRP hazard descriptions, not validated coefficients.

## Quickstart

Requires Python 3.11+ (the Dockerfile uses 3.11; local testing was done on 3.10.11).

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

Open http://localhost:8000

Copy `.env.example` to `.env` to override settings.

## Docker

```bash
docker build -t orbitcare5x .
docker run -p 8000:8000 orbitcare5x
```

Open http://localhost:8000

## Single-file build

```bash
python scripts/build_single_file.py
```

This writes `dist/orbitcare5x.html`, a self-contained page with the frontend inlined. Open it in a browser. To use a running backend, add `?api=http://localhost:8000` to the URL (for example `dist/orbitcare5x.html?api=http://localhost:8000`). A page opened from `file://` sends the `null` origin, so the backend's `CORS_ORIGINS` must allow it. The default already includes `null`. If you changed `CORS_ORIGINS`, add `null` back. Without a backend, the API sections show "Backend unavailable" with a Retry control.

## Tests

```bash
python -m pytest backend/tests -q
```

## Sample data

```bash
python scripts/generate_sample.py
```

This regenerates `data/sample/workflow_a_31_scenarios.csv` and `.json` (seed 42, fully SIMULATED). The file covers 31 hazard scenarios for astronaut SIM-A1: every non-empty combination of the five hazards, plus a Day-1 nominal baseline. Upload it on Mission Control to see the grade decline across the mission.

## Architecture

**Stack:** Python, FastAPI, Uvicorn, SQLAlchemy 2, Pydantic v2, httpx, Pandas, NumPy. The frontend is HTML, CSS custom properties, and vanilla JS modules with a hash router. There is no build step. Charts use Chart.js 4, vendored locally with no CDN at runtime.

**Shared engine:** `backend/app/engine/grading.py` holds the pure grading functions. The browser and the server use the same rules.

**7-stage pipeline** (`backend/app/pipeline/`). Each stage reports records in, out, rejected, and last run:

1. **Bio-Sensors:** accepts readings from simulator, JSON ingest, CSV/JSON upload (Workflow A), or manual entry.
2. **Validation:** schema and range checks, rejects future or pre-mission timestamps and duplicates, flags spikes over 5 MAD as suspect.
3. **Processing:** per-astronaut rolling 14-day median and MAD baselines, established after 7 days of data.
4. **AI Triage:** explainable rule and statistics scoring (robust z, EWMA drift, sustained shift). No ML.
5. **5X Guards & Grading:** converts factors into Guard levels and 0–100 division sub-scores, then the Total Mission Grade.
6. **Med-HUD:** builds the Flight Surgeon HUD payload per astronaut.
7. **Protocols:** maps active factors to countermeasure cards and alerts, de-duplicated per day.

**Grading rules:**

- Every division starts at a Day 1 peak baseline of 100 and subtracts factor deductions, clamped to 0–100.
- Division weights for the Total: Radiation 25%, Life Support 25%, Mental Health 20%, Gravity 15%, Earth Distance 15%.
- **Compounding penalty:** if 3 or more divisions are YELLOW or RED, the total takes an automatic −10 points.
- **Bottleneck cap:** if any division scores below 35 (RED / Grade F), the total cannot exceed Grade D (54.9), regardless of the other divisions.
- Order of operations: weighted total, then the −10 penalty, then the bottleneck cap.
- Grade scale: A+ / A (90–100, Peak Optimal), B (75–89, Mild Strain), C (55–74, Degraded Readiness), D (35–54, High Risk), F (0–34, Critical).

**Database:** SQLite by default (`sqlite:///./orbitcare.db`). Set `DATABASE_URL` to use PostgreSQL. The same SQLAlchemy models serve both.

**Key API routes:** `GET /api/health`, `POST /api/telemetry/upload`, `POST /api/telemetry/ingest`, `GET /api/telemetry` (raw stored rows), `GET /api/assessments`, `GET /api/pipeline/status`, `GET /api/spaceweather`, `POST /api/spaceweather/refresh`, `GET /api/settings`. The full contract is in `docs/CONTRACT.md`.

## Data honesty

- Every number carries an origin badge: **LIVE**, **CACHED**, **SIMULATED**, **USER-ENTERED**, or **ESTIMATE**.
- Space weather is polled from NOAA SWPC and cached (NOAA about every 60 s, DONKI about every 300 s, OSDR about every 600 s). Each input shows its age and is marked stale past its limit (30 min for proton flux, 48 h for health records).
- A failed live call is shown as a **FAILED** status with its reason and a retry control. It is never silently replaced with cached or simulated data.
- NOAA proton flux is never converted into astronaut dose. Dose comes from dose records plus a visible modelled baseline.
- "Bone load" is an exercise-loading index. The product does not predict bone density or bone loss.

## Sections and status

| Section | Status |
|---|---|
| Mission Control | Built |
| Space Weather | Built |
| Radiation Guard | Built |
| Crew Health & Mental Health Guard | Built |
| Gravity, Life Support, Earth Distance Guards | Built |
| AI Risk Analysis | Built |
| Flight Surgeon HUD | Built |
| Alerts | Built |
| Mission Simulator | Built |
| Reports & Analytics | Built |
| Settings | Built |
| NASA Research (OSDR) | Not connected |
| Roadmap extension hooks (wearables, ECLSS links, predictive ML) | Not connected |

## Known limits

- Tested locally on Python 3.10.11 only. The Docker image targets Python 3.11, which has not been run here.
- Not run here: node:test and Playwright E2E tests (node is not installed), and the Docker image build (Docker build verification is outstanding).
- Git is not installed. Milestones are snapshotted as zip files in `checkpoints/`.
- Crew, vitals, and cabin telemetry are simulated. Predictive ML and offline triage AI are roadmap items. Current triage is an explainable rule-based decision tree.

## Documentation

- `PLAN.md`: the master build prompt and product plan
- `docs/CONTRACT.md`: interface contract (source of truth for API and grading)
- `docs/ASSUMPTIONS.md`: assumptions and illustrative defaults
- `docs/PROGRESS.md`: milestone status
- `docs/TEST_REPORT.md`: test results
- `docs/DEMO_SCRIPT.md`: 5-minute demo script
