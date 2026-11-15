# ORBITCARE 5X — Progress

## Done
- M0 scaffold: requirements.txt, .env.example, .gitignore, Dockerfile, backend package skeleton, `GET /api/health`, conditional static mount of frontend/, frontend/index.html placeholder with disclaimer footer.
- CONTRACT: docs/CONTRACT.md (interface contract, source of truth).
- M1 grading engine: backend/app/engine/config.py and grading.py (CONTRACT §3), 14 golden tests passing.
- Simulated 31-scenario sample data (seed 42, fully SIMULATED).

## In progress
- M2 backend pipeline and API (CONTRACT §1 data models and db.py, 7-stage pipeline, telemetry/assessment API per CONTRACT §4).
- M3 frontend sections per CONTRACT §1 and PLAN §5.

## Decisions
- Frontend mount is conditional on frontend/ existing, so the API runs before the UI exists.
- Dockerfile uses python:3.11-slim (PLAN §4 requires Python 3.11+); local dev Python on this machine is 3.10.11.
- .gitignore does not ignore dist/ (single-file build output must be committed).
- Zip checkpoints instead of git commits: git is not installed, so milestones are snapshotted as zip files in checkpoints/ until git is available.

## Status (2026-11-14)

**Done**
- M0 to M7: all milestones built. Backend pytest suite passes (36 passed). Single-file build produces `dist/orbitcare5x.html`.
- M7: Mission Simulator, Reports & Analytics, Settings, single-file build, demo script and README updated.

**Not done**
- Playwright and node:test E2E tests (node is not installed).
- Docker build verification.
- NASA Research (OSDR) integration (shown as a labelled not-connected panel).

**Next**
- Playwright and node:test E2E tests once node is installed.
- Docker build verification.
- NASA Research OSDR integration.
- `git init` and first commit once git is installed.
