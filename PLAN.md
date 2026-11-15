
ORBITCARE 5X: Final Master Build Prompt (v3 — 5-Division & Total Mission Grading)Nov 14, 2026 · @javvaji pranay · NASA Space Apps Challenge 2026Includes Workflow A Batch Time-Series Uploads, 5 Hazard Division Sub-Scores (A+ to F), and a Derived Total Mission Division Grade with Bottleneck & Compounding Rules.
1. Role, Order of Authority and Working Rules
Paste this whole document into the coding tool as one prompt. It integrates the Workflow A time-series batch upload UX and the explicit 5-Division + Total Mission Derived Grading Architecture.
Your role. Act as a senior full-stack engineer, aerospace software engineer, space-medicine informatics specialist and UI/UX designer. Build a complete, runnable web application called ORBITCARE 5X. A static page, slide deck, mock-up or decorative dashboard is a failed delivery: every button, chart, form and export must work.
Order of Authority When Instructions Conflict
Section 3 (guardrails on science, safety and honesty) beats everything.
The PPT plan in Section 2 (five hazards, five Guards, 7-stage loop, Flight Surgeon HUD, roadmap) beats the earlier prompts on scope and structure.
Sections 4 to 10 of this document beat the earlier prompts on detail.
The earlier prompts fill any gap this document leaves.
Conflicts Already Resolved
Topic
PPT Plan
Earlier Prompts
Decision
Scope
Five hazards, five Guards, Flight Surgeon HUD
Ten radiation-led modules
Build both: the ten modules plus 5X Guards, 5-Division Grading + Total Derived Grade, and the HUD (12 sections total)
Stack
Python, Streamlit, Plotly, ML
FastAPI, HTML/JS, Chart.js, SQLite
FastAPI serving a website, because a website was requested. Python, Pandas, NumPy kept. Chart.js for charts.
Data
Simulated telemetry
Live NASA and NOAA data
Space weather is live (cached polling). Crew vitals and cabin telemetry are simulated, batch-uploaded (Workflow A), or user-entered.
AI
AI triage, predictive ML
No unvalidated ML claims
Explainable rules plus robust statistics and 5-Division + Total Derived Grading now. Predictive ML on roadmap
Tagline word 'Predicting'
Tagline on slide 8
No prediction claims
Keep the tagline. In the interface call outputs 'early-warning screening'

Working Rules
If a project folder is supplied, inspect every file first, list what works and what is broken, keep working features, then extend. If none is supplied, build from scratch.
Write a short plan, then implement it in the same session. Do not stop after planning or after sample code.
No decorative controls, no TODO stubs, no invented live data.
Test as you go and claim only what you ran. Paste real command output into the test report.
If something cannot be done with the available data or hardware, build the extension hook, label it 'not connected', and say so in the README and interface.
Do not ask clarifying questions. Where silent, choose the conservative option and record in docs/ASSUMPTIONS.md.
2. Product Vision and the Submitted PPT Plan
ORBITCARE 5X unites NASA's five Human Research Program hazards in one onboard decision-support platform, featuring dedicated hazard division grading and a derived Total Mission Grade. Tagline: Protecting Astronauts. Predicting Risks. Powering the Future of Space Exploration. Event: NASA Space Apps Challenge 2026.
Slide
What the Plan Says
What You Build
1
Five NASA hazards; hazards interact synergistically
A hazard configuration for all five; hazard ring on Mission Control; interaction watch rules (Section 6)
2
Crew biometric ingestion; cross-hazard scoring; Flight Surgeon HUD
Telemetry ingest API, simulator, Workflow A time-series file upload (CSV/JSON), 5-Division + Total Derived Grading engine, HUD section
3
Five Guard modules
Five Guard engines, each with its own page/tab plus an explicit 0–100 Division Grade sub-score
4
7-stage loop: Bio-Sensors, Validation, Processing, AI Triage, 5X Guards, Med-HUD, Protocols
Seven real code stages that each report records in, out, rejected and last run
5
Simulated telemetry demo; Python, Pandas, NumPy
A labelled simulated generator (with optional frontend interval tick), Pandas/NumPy pipeline, TelemetrySource adapter
6
5-in-1 hazard fusion; human and habitat link; predictive risk triage
Assessment across all Guards with 5 Division Grades and a Derived Total Mission Grade; vitals correlated with cabin readings; latency tiers
7
Roadmap: wearables, ECLSS links, predictive ML, offline triage AI
Extension hooks and Roadmap panel marked 'not connected'. Offline triage is a rule-based decision tree
8
Vision statement and tagline
About panel and footer carrying the vision quote exactly as written in the PPT

The Five Hazards and the Guard That Owns Each
Hazard (Slide 1)
PPT Wording
Guard
Division Sub-Score & Inputs
Space Radiation
DNA damage and elevated cellular health risks
Radiation Guard
Radiation Division Sub-Score (0–100); Dose records, NOAA & DONKI solar particle indicators
Distance From Earth
Delayed telemedicine and autonomous care needs
Earth Distance Guard
Earth Distance Division Sub-Score (0–100); Signal latency, link status, open medical flags
Gravity Fields
Bone density loss, muscle atrophy, fluid shifts
Gravity Health Guard
Gravity Division Sub-Score (0–100); Resistive exercise loading index, vestibular balance score
Closed Ecosystems
Cabin air quality, microbes, immune shifts
Life Support Guard
Life Support Division Sub-Score (0–100); Cabin O2, CO2, pressure, scrubber state
Isolation & Stress
Circadian disruption and cognitive fatigue
Mental Health Guard
Mental Health Division Sub-Score (0–100); HRV stress, sleep debt, fatigue, stress

3. Non-Negotiable Guardrails
These rules apply to every screen, report, alert and line of generated text. Break none of them to add a feature.
Data Honesty
Never fabricate live data. Every number shows its origin: LIVE, CACHED, SIMULATED, USER-ENTERED or ESTIMATE.
A failed live call is shown as a failure with its reason and retry control. Never replace silently.
All demo crew, vitals, permutation uploads, and cabin telemetry is simulated, about fictional people, and labelled SIMULATED everywhere.
Show the age of every input and mark it stale past its limit (30 min proton flux, 48 h health records).
Science & Readiness Grading Honesty
Never convert NOAA proton flux into astronaut dose. Dose comes from dose records plus a visible modelled baseline.
Reference thresholds are configurable assumptions. Defaults carry a source note or 'illustrative default'.
'Bone load' is an exercise-loading index. Never call it bone density or predict bone loss.
The 5 Division Grades and Total Mission Grade (0–100, Grade A+ to F) start from a Day 1 peak baseline of 100. Label them: 'Readiness & Condition Index — Illustrative screening metric, not a medical diagnosis'.
Hazard interaction rules are hypotheses drawn from HRP hazard descriptions, not validated coefficients.
AI Claims & Medical Safety
AI triage means an explainable rule-and-statistics engine. No forecasting claims of solar events.
Product is not a medical diagnostic system or device. State this in footers, HUD, and health reports.
Countermeasure and triage guidance defers to the flight surgeon and mission procedures. Never name medications/dosages.
4. Stack, Architecture, Ingestion Cadence & Repository Layout
Build a Python backend that serves a dependency-light website, with one shared calculation engine (including dose, Guard levels, cross-hazard fusion, and the 5-Division + Total Derived Grading rules) so the browser and server agree.
Layer
Use
Notes
Backend
Python 3.11+, FastAPI, Uvicorn, SQLAlchemy 2, Pydantic v2, httpx
Async upstream calls with timeouts and retries
Data processing
Pandas, NumPy
Pipeline stages, proton-flux cleaning, personal baselines
Database
SQLite by default; PostgreSQL by setting DATABASE_URL
Same models for both. Document migration path
Frontend
HTML, CSS custom properties, vanilla JS modules, hash router
No build step. Served by FastAPI. Includes optional interval tick
Charts
Chart.js 4, vendored locally
No CDN at runtime. Includes Grade Trajectory Overlay
Tests
pytest, httpx MockTransport, node:test, Playwright
See Section 9
Packaging
requirements.txt, .env.example, Dockerfile
Plus single-file HTML build

Telemetry Ingestion & Demo Cadence (Workflow A + Pseudo-Real-Time Simulation)1. Periodic Space Weather Polling: External feeds (NOAA 60s, DONKI 300s, OSDR 600s) use cached polling with manual refresh.2. Workflow A (Single-File Time-Series Upload): Users drop a single multi-timestamp CSV or JSON telemetry file (e.g. 31 hazard permutation scenarios) on Mission Control or Settings. The backend ingests all chronological rows through the 7-stage pipeline, immediately plotting the astronaut's 5-division and Total Mission deterioration curve from Day 1 peak condition (Grade A+) down to degraded/critical states.3. Pseudo-Real-Time Frontend Loop: Toggleable 'Live Simulation Stream' button in the UI using a frontend JavaScript setInterval (every 3–5s) posting incremental simulated readings to POST /api/telemetry/ingest.

5. The 12 Application Sections
Build twelve sections in navigation order. Each works on its own with loading, empty, and error states.
5.1 Mission Control
Mission elapsed time, planned duration, day n of N, and quick Workflow A CSV/JSON upload bar.
Five Hazards Ring & Division Summary: Five tiles (Radiation, Distance, Gravity, Closed Ecosystem, Isolation & Stress), each GREEN, YELLOW or RED with its 0–100 division sub-score and letter grade.
Total Mission Health Grade Badge: Prominently displayed composite derived grade (0–100, Grade A+ to F) computed from the 5 divisions, with delta since Day 1.
Space-weather status, crew list with division grades, API connectivity table, and schematic Earth-Moon/Mars progress bar.
5.2 Space Weather & 5.3 Radiation Guard
Space Weather: NOAA SWPC proton flux, X-ray flux, Kp, scales; DONKI flares/CMEs/SEPs; simulated storm rehearsal (S1/S3).
Radiation Guard: Dose records, cumulative dose vs 600 mSv threshold, Radiation Division Readiness Sub-Score (0–100), shielding forecasts, CSV/PDF exposure export.
5.4 Crew Health & Mental Health Guard
Vitals records (heart rate, HRV RMSSD, sleep, fatigue, stress), UTC timestamps, CSV/JSON file upload.
Astronaut Health Grade & Trajectory Panel: Placed alongside vital monitoring graphs. Displays the derived Total Mission Grade, delta from Day 1 peak (100), 5-Bar Division Breakdown (Radiation, Mental Health, Gravity, Life Support, Earth Distance), and Grade Trajectory Overlay.
Trend charts, personal baseline band (median ± MAD), and Mental Health Guard metrics.
5.5 5X Guards: Gravity, Life Support, Earth Distance
Three dedicated tabs, each displaying its respective Division Sub-Score (0–100, A+ to F):
Gravity Health Guard: Resistive exercise loading index vs target, vestibular balance score (0–100), activity counts.
Life Support Guard: Cabin O2, CO2, pressure, temp, humidity, AQI, scrubber state, human-and-habitat link overlay.
Earth Distance Guard: Distance, light-time, latency tiers (Tier 1 <2s, Tier 2 2–60s, Tier 3 >60s), queue length, offline triage launcher.
5.6 AI Risk Analysis & 5.7 Flight Surgeon HUD (Med-HUD)
AI Risk: Overall and per-astronaut results from fusion & grading engine, factors table, confidence, reasoning list, interaction watch flags.
Flight Surgeon HUD: Glanceable per-astronaut view with 5 Guard rings, prominent Total Mission Grade badge and 5-hazard division score bars in header, vitals sparklines, cabin readings, early-warning list, countermeasure cards, offline rule-based triage, and delay sync controls.
5.8 Mission Simulator to 5.12 Settings
Mission Simulator (real-time recalculation of trajectory and grades), NASA Research (OSDR search), Alerts Centre (de-duplicated rules, severity filters, shelter banner), Reports & Analytics (PDF/CSV exports), Settings (profiles, thresholds, grading weights, backup/restore).
6. Engines: Dose, Guard Scoring, 5-Division & Total Derived Grading
6.1 Dose Engine & 6.2 Guard Scoring & Division Sub-Scores (0–100)
Each Guard turns its inputs into factors and computes an explicit 0–100 Readiness Division Sub-Score starting from a Day 1 peak baseline of 100:
Radiation Division Sub-Score: Deducts proportionally as cumulative career dose approaches 600 mSv and during active SEP/flares/protons >=10 pfu.
Mental Health Division Sub-Score: Deducts for sleep <6h, HRV RMSSD drop vs personal baseline, and rising fatigue/stress slopes.
Gravity Division Sub-Score: Deducts when weekly resistive exercise-loading index drops below 80% of target or vestibular balance declines.
Life Support Division Sub-Score: Deducts when cabin CO2 >5,000 ppm, O2 drifts, or scrubber state is degraded/offline.
Earth Distance Division Sub-Score: Deducts when latency enters Tier 2 or Tier 3 while another hazard division is flagged.
6.3 Cross-Hazard Fusion & Total Mission Derived Grading Architecture
The Total Mission Grade is derived directly from the 5 hazard division scores using a hybrid weighted-average and bottleneck rule:
Weighted Base Contribution: Radiation (25%), Life Support (25%), Mental Health (20%), Gravity (15%), Earth Distance (15%).
The Critical Bottleneck Rule (Safety Override): If any single hazard division drops into the RED / Grade F zone (< 35 points), the Total Mission Division Grade cannot exceed Grade D, regardless of how well the other four divisions perform.
Compounding Penalty: If 3 or more divisions fall simultaneously into YELLOW or RED, an automatic -10 point compounding penalty is applied to the final derived total score.
Total Grade Scale: 90–100 = Grade A+ to A (Peak Optimal); 75–89 = Grade B (Mild Strain); 55–74 = Grade C (Degraded Readiness); 35–54 = Grade D (High Risk); 0–34 = Grade F (Critical).
Interaction Watch Hypotheses: Radiation + Mental Health, Gravity + Mental Health, Life Support + Mental Health (labelled as hypotheses from HRP hazard descriptions).
6.4 The 7-Stage Pipeline in Code
#
Stage
What It Does
Reports
1
Bio-Sensors
Accepts readings from TelemetrySource adapters: simulated generator, JSON ingest, CSV upload (Workflow A time-series batches), manual entry. Stamps source and received time
Records received per source
2
Validation
Schema & range checks. Rejects future timestamps (>5 min) or before mission start, and duplicates. Flags spikes (>5 MAD) as suspect
Accepted, rejected with reason, suspect
3
Processing
Per-astronaut, per-metric baseline: rolling 14-day median and MAD, established after 7 days of data. Robust z
Baseline established or not
4
AI Triage
Explainable anomaly scoring: robust z (>=3), EWMA drift, sustained-shift check
Anomalies with values
5
5X Guards & Grading
Converts factors into the five Guard levels and computes explicit 0–100 sub-scores for all 5 Divisions plus the Derived Total Mission Grade
Level & score per Division
6
Med-HUD
Builds HUD payload for each astronaut including Division grades and Total Grade trajectory
Payload age
7
Protocols
Maps active factors to countermeasure cards and alerts, de-duplicated per day
Alerts created

7. Data Model, Backend API & External Data
Includes SQLite/PostgreSQL schemas (missions, astronauts, dose_records, health_records, exercise_sessions, balance_tests, cabin_telemetry, comm_link_log, assessments, alerts, settings), unified Workflow A endpoints (POST /api/telemetry/upload and /ingest), and NOAA/DONKI/OSDR cached proxies.
8. UI, UX, Accessibility & Offline Behaviour
Dark aerospace console theme (#050b1a background, cyan accents, high contrast status tokens), responsive layout (sidebar >=980px, bottom bar + drawer <980px), accessibility standards, and Flight Surgeon HUD high-contrast view.
9. Testing, Acceptance & Build Gates & 10. Deliverables & Demo Script
Comprehensive test suite (dose golden cases, division grading validation, 64-case parity test, Playwright E2E). Deliverables include repository, single-file offline build (dist/orbitcare5x.html), full documentation, and the updated 5-minute hackathon demo script showcasing Workflow A batch upload and the 5-division + Total Mission grade decline.
