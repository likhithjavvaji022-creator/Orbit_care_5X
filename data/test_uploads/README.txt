TEST UPLOAD FILES (all data is SIMULATED, fictional astronauts)
================================================================
Upload these on Mission Control (upload bar). Each file has 8 days:
Day 1 is normal, days 2-8 have the listed hazards switched on.
Each file uses a different astronaut ID, so you can upload them one after another.
Recreate them with:  python scripts/make_test_uploads.py

Result after the last day (checked by uploading every file on 2026-11-15):

File                                    Astronaut     Final grade   What to notice
--------------------------------------  ------------  ------------  -----------------------------------------
01_radiation_only.csv                   SIM-RAD       90.7  A       Radiation tile turns YELLOW
02_mental_health_only.csv               SIM-MH        54.9  D       Mental Health RED -> total capped at D
03_gravity_only.csv                     SIM-GRAV      93.1  A       Gravity tile YELLOW
04_life_support_only.csv                SIM-LS        85.2  B       Life Support YELLOW (high CO2, scrubber degraded)
05_earth_distance_only.csv              SIM-ED        97.0  A+      Stays GREEN: the delay only costs points when
                                                                    another hazard is also flagged
06_radiation_plus_mental_health.csv     SIM-RAD-MH    54.9  D       Capped at D; "interaction watch" flag
07_life_support_plus_mental_health.csv  SIM-LS-MH     54.9  D       Capped at D; interaction flag
08_gravity_plus_mental_health.csv       SIM-GRAV-MH   54.9  D       Capped at D; interaction flag
09_three_hazards_grav_ls_mh.csv         SIM-3HAZ      54.2  D       3 hazards flagged -> extra -10 penalty
10_all_five_hazards.csv                 SIM-ALL5      40.4  D       All 5 flagged: cap + -10 penalty
11_life_support_only.json               SIM-LS-JSON   85.0  B       Same as 04 but a JSON file
12_validation_errors.csv                SIM-BAD       98.5  A+      3 rows accepted, 3 rejected: duplicate,
                                                                    future date, impossible sleep value (-3 h)

Note: uploading the same file twice rejects every row as a duplicate. To start fresh,
use Settings -> Reset demo data.
