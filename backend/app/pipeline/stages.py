"""The 7 pipeline stages (PLAN 6.4). Each takes a Ctx, mutates it, returns a StageReport."""
import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from ..engine.grading import assess
from ..models import AlertRecord, Astronaut, AssessmentRecord, HealthRecord, Mission

COLUMNS = [
    "timestamp", "astronaut_id", "mission_day", "scenario_id", "scenario_label",
    "cum_dose_msv", "proton_flux_pfu", "flare_active", "sleep_h", "hrv_rmssd_ms",
    "hrv_baseline_ms", "fatigue", "stress", "loading_index", "loading_target",
    "balance_score", "cabin_o2_pct", "cabin_co2_ppm", "cabin_pressure_kpa",
    "cabin_temp_c", "cabin_humidity_pct", "scrubber_state", "latency_s",
    "open_medical_flags", "source",
]
INT_FIELDS = {"mission_day", "scenario_id", "open_medical_flags"}
FLOAT_FIELDS = {
    "cum_dose_msv", "proton_flux_pfu", "sleep_h", "hrv_rmssd_ms", "hrv_baseline_ms", "fatigue",
    "stress", "loading_index", "loading_target", "balance_score", "cabin_o2_pct",
    "cabin_co2_ppm", "cabin_pressure_kpa", "cabin_temp_c", "cabin_humidity_pct", "latency_s",
}
RANGES = {  # inclusive (lo, hi); None = unbounded
    "mission_day": (1, None), "scenario_id": (0, 31), "open_medical_flags": (0, None),
    "cum_dose_msv": (0, None), "proton_flux_pfu": (0, None), "sleep_h": (0, 24),
    "hrv_rmssd_ms": (0, 500), "hrv_baseline_ms": (0, 500), "fatigue": (0, 10), "stress": (0, 10),
    "loading_index": (0, None), "loading_target": (0, None), "balance_score": (0, 100),
    "cabin_o2_pct": (0, 100), "cabin_co2_ppm": (0, 100000), "cabin_pressure_kpa": (0, 1000),
    "cabin_temp_c": (-50, 100), "cabin_humidity_pct": (0, 100), "latency_s": (0, None),
}
SCRUBBER = {"nominal", "degraded", "offline"}
SOURCES = {"SIMULATED", "USER-ENTERED", "LIVE", "CACHED", "ESTIMATE"}
DEFAULT_MISSION_START = "2026-11-01T00:00:00Z"
FUTURE_TOLERANCE = timedelta(minutes=5)
WINDOW = timedelta(days=14)
ESTABLISH_DAYS = 7
SPIKE_METRICS = ["hrv_rmssd_ms", "sleep_h", "fatigue", "stress", "cabin_co2_ppm",
                 "cabin_o2_pct", "cabin_pressure_kpa", "loading_index", "balance_score"]
BASELINE_METRICS = ["hrv_rmssd_ms", "sleep_h", "fatigue", "stress"]
STAGE_NAMES = ["Bio-Sensors", "Validation", "Processing", "AI Triage",
               "5X Guards & Grading", "Med-HUD", "Protocols"]


def now_utc():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_ts(v):
    if isinstance(v, datetime):
        dt = v
    else:
        s = str(v).strip()
        if s.endswith(("Z", "z")):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass
class Ctx:
    session: object
    raw: list
    default_source: str = "USER-ENTERED"
    items: list = field(default_factory=list)       # accepted items (chronological after stage 2)
    all_items: list = field(default_factory=list)
    rejected: list = field(default_factory=list)
    suspect: list = field(default_factory=list)
    series: dict = field(default_factory=dict)      # astronaut -> list of (dt, row) sorted
    assessments: list = field(default_factory=list)
    hud: dict = field(default_factory=dict)
    alerts_created: list = field(default_factory=list)
    anomalies: list = field(default_factory=list)
    received_at: datetime = field(default_factory=now_utc)


def report(stage, rin, rout, rejected, notes):
    return {"stage": stage, "name": STAGE_NAMES[stage - 1], "records_in": rin,
            "records_out": rout, "rejected": rejected, "last_run": iso(now_utc()), "notes": notes}


def empty_report(stage):
    r = report(stage, 0, 0, 0, "No data processed yet")
    r["last_run"] = None
    return r


# ---------- helpers ----------
def mad(vals, med=None):
    med = statistics.median(vals) if med is None else med
    return statistics.median([abs(v - med) for v in vals])


def mad_floor(m, med):
    return max(m, 0.02 * abs(med), 1e-6)


def prior_window(ctx, astro, ts):
    return [r for dt, r in ctx.series.get(astro, []) if dt < ts and ts - dt <= WINDOW]


def _values(rows, metric):
    return [r[metric] for r in rows if r.get(metric) is not None]


# ---------- stage 1 ----------
def stage1_ingest(ctx):
    counts = {}
    for i, raw in enumerate(ctx.raw, start=1):
        item = {"idx": i, "raw": raw if isinstance(raw, dict) else {}, "row": None,
                "suspect": [], "anomalies": [], "received_at": ctx.received_at}
        src = str(item["raw"].get("source") or "").strip().upper() or ctx.default_source
        item["source"] = src
        counts[src] = counts.get(src, 0) + 1
        item["is_dict"] = isinstance(raw, dict)
        ctx.all_items.append(item)
    notes = "received per source: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
    return report(1, len(ctx.raw), len(ctx.all_items), 0, notes or "no records")


# ---------- stage 2 ----------
def _coerce(raw, source):
    row = {}
    for c in COLUMNS:
        v = raw.get(c)
        if isinstance(v, str):
            v = v.strip()
        row[c] = None if v is None or v == "" else v
    row["source"] = source
    if source not in SOURCES:
        return None, f"invalid source '{source}'"
    if not row["astronaut_id"]:
        return None, "missing astronaut_id"
    row["astronaut_id"] = str(row["astronaut_id"])
    if row["timestamp"] is None:
        return None, "missing timestamp"
    try:
        dt = parse_ts(row["timestamp"])
    except (ValueError, TypeError):
        return None, f"invalid timestamp '{row['timestamp']}'"
    row["timestamp"] = iso(dt)
    for f in INT_FIELDS | FLOAT_FIELDS:
        v = row[f]
        if v is None:
            continue
        try:
            num = float(v)
            if math.isnan(num) or math.isinf(num):
                raise ValueError
            if f in INT_FIELDS:
                if num != int(num):
                    raise ValueError
                num = int(num)
        except (ValueError, TypeError):
            return None, f"invalid value for {f}: '{v}'"
        lo, hi = RANGES.get(f, (None, None))
        if (lo is not None and num < lo) or (hi is not None and num > hi):
            return None, f"{f} out of range: {num}"
        row[f] = num
    if row["mission_day"] is None:
        return None, "missing mission_day"
    fa = row["flare_active"]
    if fa is not None:
        s = str(fa).strip().lower()
        if s in ("1", "true", "yes", "1.0"):
            row["flare_active"] = 1
        elif s in ("0", "false", "no", "0.0"):
            row["flare_active"] = 0
        else:
            return None, f"invalid value for flare_active: '{fa}'"
    sc = row["scrubber_state"]
    if sc is not None:
        sc = str(sc).lower()
        if sc not in SCRUBBER:
            return None, f"invalid scrubber_state '{sc}'"
        row["scrubber_state"] = sc
    return row, dt


def stage2_validate(ctx):
    s = ctx.session
    stored = s.execute(select(HealthRecord).order_by(HealthRecord.timestamp)).scalars().all()
    seen = set()
    for r in stored:
        seen.add((r.astronaut_id, r.timestamp))
        row = {c: getattr(r, c) for c in COLUMNS}
        ctx.series.setdefault(r.astronaut_id, []).append((parse_ts(r.timestamp), row))
    mission = s.execute(select(Mission).order_by(Mission.id)).scalars().first()
    now = now_utc()

    parsed = []
    for item in ctx.all_items:
        if not item["is_dict"]:
            ctx.rejected.append({"row": item["idx"], "reason": "row is not an object"})
            continue
        row, dt = _coerce(item["raw"], item["source"])
        if row is None:
            ctx.rejected.append({"row": item["idx"], "reason": dt})
            continue
        item["row"], item["dt"] = row, dt
        parsed.append(item)

    if mission:
        start = parse_ts(mission.start)
    elif parsed or stored:
        cands = [i["dt"] for i in parsed] + [dt for rows in ctx.series.values() for dt, _ in rows]
        start = min(cands)  # no mission configured: earliest row defines the start
    else:
        start = parse_ts(DEFAULT_MISSION_START)

    parsed.sort(key=lambda i: (i["dt"], i["idx"]))
    for item in parsed:
        row, dt = item["row"], item["dt"]
        key = (row["astronaut_id"], row["timestamp"])
        # SIMULATED mission-time rows are exempt from the future check (sample spans mission days ahead).
        if row["source"] != "SIMULATED" and dt > now + FUTURE_TOLERANCE:
            ctx.rejected.append({"row": item["idx"], "reason": "timestamp in the future (>5 min)"})
            continue
        if dt < start:
            ctx.rejected.append({"row": item["idx"], "reason": f"timestamp before mission start {iso(start)}"})
            continue
        if key in seen:
            ctx.rejected.append({"row": item["idx"], "reason": "duplicate astronaut_id+timestamp"})
            continue
        seen.add(key)
        prior = prior_window(ctx, row["astronaut_id"], dt)
        for m in SPIKE_METRICS:
            vals = _values(prior, m)
            if row[m] is None or len(vals) < ESTABLISH_DAYS:
                continue
            med = statistics.median(vals)
            md = mad_floor(mad(vals, med), med)
            if abs(row[m] - med) > 5 * md:
                reason = f"{row[m]} deviates >5 MAD from rolling median {round(med, 2)}"
                item["suspect"].append({"row": item["idx"], "metric": m, "reason": reason})
        ctx.suspect.extend(item["suspect"])
        ctx.items.append(item)
        ctx.series.setdefault(row["astronaut_id"], []).append((dt, row))
    for rows in ctx.series.values():
        rows.sort(key=lambda t: t[0])
    ctx.rejected.sort(key=lambda r: r["row"])
    notes = (f"accepted {len(ctx.items)}, rejected {len(ctx.rejected)}, "
             f"suspect {len(ctx.suspect)} (spikes >5 MAD)")
    return report(2, len(ctx.all_items), len(ctx.items), len(ctx.rejected), notes)


# ---------- stage 3 ----------
def stage3_baseline(ctx):
    established = 0
    for item in ctx.items:
        row, dt = item["row"], item["dt"]
        prior = prior_window(ctx, row["astronaut_id"], dt)
        days = {r["timestamp"][:10] for r in prior}
        ok = len(days) >= ESTABLISH_DAYS
        base = {}
        if ok:
            for m in BASELINE_METRICS:
                vals = _values(prior, m)
                if len(vals) >= 3:
                    med = statistics.median(vals)
                    base[m] = {"median": round(med, 3), "mad": round(mad(vals, med), 3), "n": len(vals)}
            if row["hrv_baseline_ms"] is None and "hrv_rmssd_ms" in base:
                row["hrv_baseline_ms"] = base["hrv_rmssd_ms"]["median"]
        item["baseline"] = {"established": ok, "days": len(days), "metrics": base}
        established += ok
    notes = (f"baseline established for {established}/{len(ctx.items)} records "
             f"(rolling 14-day median/MAD, after {ESTABLISH_DAYS} days)")
    return report(3, len(ctx.items), len(ctx.items), 0, notes)


# ---------- stage 4 ----------
def stage4_triage(ctx):
    for item in ctx.items:
        row, dt, b = item["row"], item["dt"], item["baseline"]
        if not b["established"]:
            continue
        prior = prior_window(ctx, row["astronaut_id"], dt)
        for m, st in b["metrics"].items():
            x = row.get(m)
            if x is None:
                continue
            vals = _values(prior, m)
            med = st["median"]
            sd = 1.4826 * mad_floor(st["mad"], med)
            z = (x - med) / sd
            found = None
            if abs(z) >= 3:
                found = {"kind": "robust_z", "z": round(z, 2)}
            else:
                ew = vals[0] if vals else x
                for v in vals[1:] + [x]:
                    ew = 0.3 * v + 0.7 * ew
                dz = (ew - med) / sd
                recent = vals[-2:] + [x]
                if len(recent) == 3 and all(abs((v - med) / sd) >= 2 for v in recent) \
                        and all((v - med) * (x - med) > 0 for v in recent):
                    found = {"kind": "sustained_shift", "z": round(z, 2)}
                elif abs(dz) >= 2:
                    found = {"kind": "ewma_drift", "z": round(dz, 2)}
            if found:
                a = {"row": item["idx"], "astronaut_id": row["astronaut_id"], "metric": m,
                     "value": x, "baseline_median": med, **found}
                item["anomalies"].append(a)
                ctx.anomalies.append(a)
    notes = f"{len(ctx.anomalies)} anomalies (robust z>=3, EWMA drift, sustained shift)"
    return report(4, len(ctx.items), len(ctx.items), 0, notes)


# ---------- stage 5 ----------
def stage5_grade(ctx):
    s = ctx.session
    day1 = {}
    known = set()
    for aid in {i["row"]["astronaut_id"] for i in ctx.items}:
        first = s.execute(select(AssessmentRecord).where(AssessmentRecord.astronaut_id == aid)
                          .order_by(AssessmentRecord.timestamp).limit(1)).scalars().first()
        if first is not None and first.total_score is not None:
            day1[aid] = first.total_score
    for item in ctx.items:
        row = item["row"]
        aid = row["astronaut_id"]
        a = assess(row, day1_score=day1.get(aid))
        if aid not in day1 and a["total"]["score"] is not None:
            day1[aid] = a["total"]["score"]
        ctx.assessments.append(a)
        item["assessment"] = a
        s.add(HealthRecord(**{c: row[c] for c in COLUMNS}, received_at=item["received_at"],
                          suspect_metrics=[{"metric": x["metric"], "reason": x["reason"]} for x in item["suspect"]]))
        s.add(AssessmentRecord(astronaut_id=aid, timestamp=row["timestamp"],
                               mission_day=row["mission_day"], total_score=a["total"]["score"],
                               grade=a["total"]["grade"], payload=a))
        if aid not in known and s.get(Astronaut, aid) is None:
            s.add(Astronaut(astronaut_id=aid, name=f"Crew {aid}", source="SIMULATED"))
        known.add(aid)
    s.flush()
    capped = sum(1 for a in ctx.assessments if a["total"]["capped"])
    return report(5, len(ctx.items), len(ctx.assessments), 0,
                  f"{len(ctx.assessments)} assessments; {capped} bottleneck-capped")


# ---------- stage 6 ----------
def stage6_hud(ctx):
    s = ctx.session
    aids = sorted({a["astronaut_id"] for a in ctx.assessments})
    for aid in aids:
        recs = s.execute(select(AssessmentRecord).where(AssessmentRecord.astronaut_id == aid)
                         .order_by(AssessmentRecord.timestamp)).scalars().all()
        if not recs:
            continue
        latest = recs[-1].payload
        ctx.hud[aid] = {
            "astronaut_id": aid, "generated_at": iso(now_utc()), "latest": latest,
            "divisions": {k: {"score": d["score"], "grade": d["grade"], "status": d["status"]}
                          for k, d in latest["divisions"].items()},
            "total": latest["total"],
            "trajectory": [{"mission_day": r.mission_day, "timestamp": r.timestamp,
                            "score": r.total_score, "grade": r.grade} for r in recs],
        }
    return report(6, len(ctx.assessments), len(ctx.hud), 0,
                  f"HUD payload built for {len(ctx.hud)} astronaut(s); payload age 0 s")


# ---------- stage 7 ----------
def stage7_alerts(ctx):
    s = ctx.session
    existing = {(a.astronaut_id, a.code, a.day) for a in s.execute(select(AlertRecord)).scalars()}
    created = 0
    for a in ctx.assessments:
        aid, day = a["astronaut_id"], a["mission_day"]
        cands = []
        for k, d in a["divisions"].items():
            if d["status"] == "RED":
                cands.append((f"DIV_{k.upper()}_RED", "critical", f"{d['name']} is RED (score {d['score']})"))
            elif d["status"] == "YELLOW":
                cands.append((f"DIV_{k.upper()}_YELLOW", "warning", f"{d['name']} is YELLOW (score {d['score']})"))
        if a["total"]["capped"]:
            cands.append(("BOTTLENECK_CAP", "critical",
                          f"Total grade capped at D by critical division (score {a['total']['score']})"))
        for code, sev, msg in cands:
            key = (aid, code, day)
            if key in existing:
                continue
            existing.add(key)
            rec = AlertRecord(astronaut_id=aid, severity=sev, code=code, message=msg, day=day)
            s.add(rec)
            ctx.alerts_created.append(code)
            created += 1
    s.flush()
    return report(7, len(ctx.assessments), created, 0, f"{created} alert(s) created (de-duplicated per astronaut/code/day)")

