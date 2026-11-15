"""Grading engine: pure functions, no I/O. Illustrative screening metric, not a diagnosis."""
from .config import DEFAULT_CONFIG, DEFAULT_WEIGHTS

LABEL = "Readiness & Condition Index \u2014 Illustrative screening metric, not a medical diagnosis"
HYPOTHESIS_LABEL = "Hypothesis from HRP hazard descriptions"
NAMES = {
    "radiation": "Radiation",
    "mental_health": "Mental Health",
    "gravity": "Gravity",
    "life_support": "Life Support",
    "earth_distance": "Earth Distance",
}
ORDER = ["radiation", "mental_health", "gravity", "life_support", "earth_distance"]
PAIRS = [("radiation", "mental_health"), ("gravity", "mental_health"), ("life_support", "mental_health")]


def _c(cfg, group, key):
    return cfg[group][key]["value"]


def _num(v):
    if v is None or isinstance(v, bool):
        return None if v is None else float(v)
    if isinstance(v, (int, float)):
        return None if v != v else float(v)
    s = str(v).strip()
    if s == "" or s.lower() in ("nan", "null", "none"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _bool(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    s = str(v).strip().lower()
    if s == "":
        return None
    return s in ("1", "true", "t", "yes", "y", "1.0")


def _r1(x):
    return round(x + 1e-12, 1)


def status(score):
    if score is None:
        return "NO_DATA"
    if score >= 75:
        return "GREEN"
    if score >= 35:
        return "YELLOW"
    return "RED"


def grade_letter(score):
    if score is None:
        return None
    if score >= 95:
        return "A+"
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 55:
        return "C"
    if score >= 35:
        return "D"
    return "F"


def _factor(code, label, value, deduction):
    return {"code": code, "label": label, "value": value, "deduction": round(deduction, 2)}


def _result(key, factors, no_data=False):
    if no_data:
        return {"key": key, "name": NAMES[key], "score": None, "grade": None,
                "status": "NO_DATA", "factors": []}
    score = _r1(max(0.0, min(100.0, 100.0 - sum(f["deduction"] for f in factors))))
    return {"key": key, "name": NAMES[key], "score": score, "grade": grade_letter(score),
            "status": status(score), "factors": factors}


def score_radiation(row, cfg=DEFAULT_CONFIG):
    dose, pf, fl = _num(row.get("cum_dose_msv")), _num(row.get("proton_flux_pfu")), _bool(row.get("flare_active"))
    if dose is None and pf is None and fl is None:
        return _result("radiation", [], True)
    f = []
    if dose is not None:
        d = _c(cfg, "radiation", "max_dose_deduction") * min(dose / _c(cfg, "radiation", "career_limit_msv"), 1)
        if d > 0:
            f.append(_factor("CUM_DOSE", "Cumulative dose vs career limit", dose, d))
    if pf is not None and pf >= _c(cfg, "radiation", "proton_flux_pfu"):
        f.append(_factor("PROTON_FLUX", "Proton flux >= threshold", pf, _c(cfg, "radiation", "proton_deduction")))
    if fl:
        f.append(_factor("FLARE_ACTIVE", "Solar flare active", 1, _c(cfg, "radiation", "flare_deduction")))
    return _result("radiation", f)


def score_mental_health(row, cfg=DEFAULT_CONFIG):
    sl, hrv, base = _num(row.get("sleep_h")), _num(row.get("hrv_rmssd_ms")), _num(row.get("hrv_baseline_ms"))
    fa, st = _num(row.get("fatigue")), _num(row.get("stress"))
    if sl is None and hrv is None and fa is None and st is None:
        return _result("mental_health", [], True)
    g = lambda k: _c(cfg, "mental_health", k)
    f = []
    if sl is not None:
        if sl < g("sleep_severe_h"):
            f.append(_factor("SLEEP_SEVERE", "Sleep below severe threshold", sl, g("sleep_severe_deduction")))
        elif sl < g("sleep_low_h"):
            f.append(_factor("SLEEP_LOW", "Sleep below 6 h", sl, g("sleep_low_deduction")))
    if hrv is not None and base is not None and base > 0:
        drop = max(0.0, (base - hrv) / base * 100)
        if drop > 0:
            f.append(_factor("HRV_DROP", "HRV RMSSD drop vs baseline (%)", round(drop, 2), min(g("hrv_max_deduction"), drop)))
    if fa is not None and fa > g("fatigue_free"):
        f.append(_factor("FATIGUE", "Fatigue above 5", fa, (fa - g("fatigue_free")) * g("fatigue_coeff")))
    if st is not None and st > g("stress_free"):
        f.append(_factor("STRESS", "Stress above 5", st, (st - g("stress_free")) * g("stress_coeff")))
    return _result("mental_health", f)


def score_gravity(row, cfg=DEFAULT_CONFIG):
    li, lt, bal = _num(row.get("loading_index")), _num(row.get("loading_target")), _num(row.get("balance_score"))
    ratio = li / lt if (li is not None and lt) else None
    if ratio is None and bal is None:
        return _result("gravity", [], True)
    g = lambda k: _c(cfg, "gravity", k)
    f = []
    if ratio is not None and ratio < g("loading_ratio_min"):
        f.append(_factor("LOADING_LOW", "Resistive loading below 80% of target (ratio)", round(ratio, 3),
                         min(g("loading_max_deduction"), (g("loading_ratio_min") - ratio) * g("loading_coeff"))))
    if bal is not None and bal < g("balance_min"):
        f.append(_factor("BALANCE_LOW", "Vestibular balance score low", bal,
                         min(g("balance_max_deduction"), (g("balance_min") - bal) * g("balance_coeff"))))
    return _result("gravity", f)


def score_life_support(row, cfg=DEFAULT_CONFIG):
    o2, co2, p = _num(row.get("cabin_o2_pct")), _num(row.get("cabin_co2_ppm")), _num(row.get("cabin_pressure_kpa"))
    sc = row.get("scrubber_state")
    sc = str(sc).strip().lower() if sc is not None and str(sc).strip() != "" else None
    if o2 is None and co2 is None and p is None and sc is None:
        return _result("life_support", [], True)
    g = lambda k: _c(cfg, "life_support", k)
    f = []
    if co2 is not None and co2 > g("co2_ppm_max"):
        f.append(_factor("CO2_HIGH", "Cabin CO2 above 5000 ppm", co2, min(g("co2_max_deduction"), (co2 - g("co2_ppm_max")) / g("co2_per_ppm"))))
    if o2 is not None and (o2 < g("o2_min_pct") or o2 > g("o2_max_pct")):
        dist = g("o2_min_pct") - o2 if o2 < g("o2_min_pct") else o2 - g("o2_max_pct")
        f.append(_factor("O2_OUT_OF_RANGE", "Cabin O2 outside 19.5-23.5 %", o2, min(g("o2_max_deduction"), dist * g("o2_coeff"))))
    if p is not None and (p < g("pressure_min_kpa") or p > g("pressure_max_kpa")):
        dist = g("pressure_min_kpa") - p if p < g("pressure_min_kpa") else p - g("pressure_max_kpa")
        f.append(_factor("PRESSURE_OUT_OF_RANGE", "Cabin pressure outside 97-103 kPa", p, min(g("pressure_max_deduction"), dist * g("pressure_coeff"))))
    if sc == "degraded":
        f.append(_factor("SCRUBBER_DEGRADED", "CO2 scrubber degraded", sc, g("scrubber_degraded_deduction")))
    elif sc == "offline":
        f.append(_factor("SCRUBBER_OFFLINE", "CO2 scrubber offline", sc, g("scrubber_offline_deduction")))
    return _result("life_support", f)


def score_earth_distance(row, others, cfg=DEFAULT_CONFIG):
    lat, flags = _num(row.get("latency_s")), _num(row.get("open_medical_flags"))
    if lat is None and flags is None:
        return _result("earth_distance", [], True)
    g = lambda k: _c(cfg, "earth_distance", k)
    f = []
    if lat is not None:
        tier = 1 if lat < g("tier1_latency_lt_s") else (2 if lat <= g("tier2_latency_max_s") else 3)
        any_bad = any((o or {}).get("status") in ("YELLOW", "RED") for o in (others or {}).values())
        if tier >= 2 and any_bad:
            f.append(_factor("LATENCY_TIER%d" % tier, "Comms latency tier %d while another division is not GREEN" % tier,
                             lat, g("tier2_deduction") if tier == 2 else g("tier3_deduction")))
    if flags is not None and flags > 0:
        f.append(_factor("OPEN_MEDICAL_FLAGS", "Open medical flags", int(flags),
                         min(g("flag_max_deduction"), flags * g("flag_deduction"))))
    return _result("earth_distance", f)


def total_grade(divisions, weights=DEFAULT_WEIGHTS, cfg=DEFAULT_CONFIG, day1_score=None):
    scored = {k: d for k, d in divisions.items() if d.get("score") is not None}
    wsum = sum(weights.get(k, 0) for k in scored)
    if not scored or wsum <= 0:
        return {"weighted": None, "penalty": 0, "capped": False, "score": None, "grade": None,
                "status": "NO_DATA", "delta_from_day1": None}
    weighted = sum(weights.get(k, 0) * d["score"] for k, d in scored.items()) / wsum
    t = lambda k: _c(cfg, "total", k)
    n_bad = sum(1 for d in scored.values() if d["status"] in ("YELLOW", "RED"))
    penalty = t("compound_penalty") if n_bad >= t("compound_count") else 0
    score = weighted + penalty
    capped = False
    if any(d["score"] < t("bottleneck_below") for d in scored.values()):
        capped = True
        score = min(score, t("bottleneck_cap"))
    score = _r1(max(0.0, min(100.0, score)))
    base = 100.0 if day1_score is None else day1_score
    return {"weighted": _r1(weighted), "penalty": penalty, "capped": capped, "score": score,
            "grade": grade_letter(score), "status": status(score), "delta_from_day1": round(score - base, 1)}


def assess(row, cfg=DEFAULT_CONFIG, weights=DEFAULT_WEIGHTS, day1_score=None):
    divs = {
        "radiation": score_radiation(row, cfg),
        "mental_health": score_mental_health(row, cfg),
        "gravity": score_gravity(row, cfg),
        "life_support": score_life_support(row, cfg),
    }
    divs["earth_distance"] = score_earth_distance(row, dict(divs), cfg)
    divs = {k: divs[k] for k in ORDER}
    total = total_grade(divs, weights, cfg, day1_score)
    flags = [{"pair": [a, b], "label": HYPOTHESIS_LABEL} for a, b in PAIRS
             if divs[a]["status"] in ("YELLOW", "RED") and divs[b]["status"] in ("YELLOW", "RED")]
    md = _num(row.get("mission_day")); sid = _num(row.get("scenario_id"))
    return {"astronaut_id": row.get("astronaut_id"), "timestamp": row.get("timestamp"),
            "mission_day": None if md is None else int(md),
            "scenario_id": None if sid is None else int(sid),
            "scenario_label": row.get("scenario_label"), "source": row.get("source"),
            "divisions": divs, "total": total, "interaction_flags": flags, "label": LABEL}
