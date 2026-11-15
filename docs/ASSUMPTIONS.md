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
