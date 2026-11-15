# ORBITCARE 5X — Test Report

## M1 grading engine (date 2026-11-14)

Command:

```
python -m pytest backend/tests/test_grading.py -q
```

Output:

```
..............                                                           [100%]
14 passed in 0.04s
```

Exit code: 0. Result: 14 passed, 0 failed.

## M2+M6 backend (2026-11-14)

Command: `python -m pytest backend/tests -q`

```
..........................                                               [100%]
============================== warnings summary ===============================
..\..\AppData\Local\Programs\Python\Python310\lib\site-packages\fastapi\testclient.py:1
  C:\Users\srila\AppData\Local\Programs\Python\Python310\lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
26 passed, 1 warning in 3.00s
```

## M3/M4 browser E2E (manual, built-in browser pane)

- Upload of 32-row sample: received 32, accepted 32, rejected 0, suspect 53, 7 stages shown.
- 5 tiles. Total 39.6 D YELLOW, delta -58.9, with -10 penalty and bottleneck cap badges.
- 3 interaction flags.
- Trajectory: 32 points.
- Live stream added days 33-35, then stopped.
- HUD and Crew Health rendered.
- No console errors.
- 375px: no horizontal overflow.
- Note: node is absent, so node:test was not run.

## Final M7 run (2026-11-14)

Command: `python -m pytest backend/tests -q` (run from project root, real output)

```
....................................                                     [100%]
============================== warnings summary ===============================
..\..\AppData\Local\Programs\Python\Python310\lib\site-packages\fastapi\testclient.py:1
  C:\Users\srila\AppData\Local\Programs\Python\Python310\lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
36 passed, 1 warning in 6.34s
```

Result: 36 passed, 0 failed. The one warning is a third-party Starlette deprecation in the TestClient import.

Command: `python scripts/build_single_file.py` (real output)

```
wrote C:\Users\srila\Downloads\HACKATHON CLAUDE\dist\orbitcare5x.html (266 KB)
```

Result: single-file build written to `dist/orbitcare5x.html` (272,895 bytes on disk).

## Worker-reported browser checks (built-in browser pane)

Reported by the build worker; these are not re-run in this M7 pass.

- M5: five Guard tabs rendered, no console errors.
- M6: Space Weather LIVE (real NOAA call), AI Risk and Alerts rendered (95 alerts, de-duplicated).
- M6 FAILED/STALE path, Retry, S1/S3 rehearsal and shelter banner were NOT exercised in the browser. FAILED, CACHED and stale behaviour are covered by pytest using MockTransport.
- M7: Simulator, Reports and Settings rendered; console clean.
- Life Support Guard showed raw temperature 21.80 C and humidity 44.40 %.
- Single-file `dist/orbitcare5x.html`: offline banner shown, all routes navigate, API sections show "Backend unavailable" with Retry.
- Single-file with `?api=http://localhost:8083`: Mission Control showed Total 39.6, Grade D.

Not run: node:test (node not installed), Playwright (node absent), Docker build.
