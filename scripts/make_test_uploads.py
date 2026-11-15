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
