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
