# ORBITCARE 5X — 5-Minute Demo Script

Tagline: **Protecting Astronauts. Predicting Risks. Powering the Future of Space Exploration.**

Setup: start the app (`uvicorn backend.app.main:app --reload`) and open http://localhost:8000 with the demo data reset (Settings > Reset demo data). All crew data is SIMULATED and fictional.

| Time | Step | What to say and show |
|---|---|---|
| 0:00–0:30 | Open **Mission Control** in its empty state. | Explain the five hazards and the early-warning screening framing. Point out the empty-state message and the SIMULATED label. |
| 0:30–1:15 | Upload `data/sample/workflow_a_31_scenarios.csv` using the Workflow A upload bar. | Walk through the 7-stage pipeline counts (records in, accepted, rejected, suspect). This is a 31-day time series for fictional astronaut SIM-A1. |
| 1:15–2:00 | Show the **five hazard tiles** (Radiation, Distance, Gravity, Closed Ecosystem, Isolation & Stress), each with a GREEN, YELLOW, or RED status and a 0–100 sub-score. Then show the **Total Mission Grade** badge. | Total grade falls from **Day 1 A+** (about 98.5 in the sample, not 100, because of the 50 mSv starting dose) to **D** by the worst days. Call out the **bottleneck cap**: any division below 35 caps the total at Grade D. Call out the **−10 compounding penalty** when three or more divisions are YELLOW or RED. |
| 2:00–2:30 | Show the **Grade Trajectory Overlay** chart. | Delta from Day 1 peak (100) is shown on the chart. Each point is a day in the mission. |
| 2:30–3:00 | Toggle **Live Simulation Stream** on. | Explain that it posts simulated readings to `POST /api/telemetry/ingest` every 3–5 s. Toggle it off again. Label: SIMULATED. |
| 3:00–3:30 | Open the **Flight Surgeon HUD** for one astronaut. | Point to the five Guard rings, the Total Grade badge, the vitals sparklines, the early-warning list, and the countermeasure cards. Say that countermeasure guidance defers to the flight surgeon and mission procedures. |
| 3:30–4:00 | Open **one Guard tab** (Radiation Guard). | Show the cumulative dose against the 600 mSv reference, the Radiation Division sub-score, and the origin badges. State that dose is never derived from NOAA proton flux. |
| 4:00–4:30 | Show the **Space Weather** panel with its **LIVE** badge. | If the NOAA call fails, show the FAILED status and the retry control instead. Do not claim forecasts of solar events. |
| 4:30–4:45 | Open **Alerts**. | Show the de-duplicated alerts, severity filter, and that alerts come from the Protocols stage. |
| 4:45–5:00 | Close on the vision line and the disclaimer. | Say: "Protecting Astronauts. Predicting Risks. Powering the Future of Space Exploration." Then read the disclaimer: not a medical device or diagnostic system. Readiness & Condition Index — Illustrative screening metric, not a medical diagnosis. All crew data SIMULATED, fictional people. |

## Notes for the presenter

- Describe the scores as early-warning screening only. Do not say they predict medical outcomes.
- Mission Simulator, Reports & Analytics, and Settings are built and can be shown. Use Settings only for the reset step above.
- NASA Research (OSDR) and the roadmap hooks (wearables, ECLSS links, predictive ML) are not connected. If asked, say so.
