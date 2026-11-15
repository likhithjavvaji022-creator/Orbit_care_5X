from backend.app.engine.config import DEFAULT_WEIGHTS, DEFAULT_CONFIG
from backend.app.engine.grading import (
    assess, status, grade_letter, score_radiation, score_mental_health, score_gravity,
    score_life_support, score_earth_distance, total_grade,
)


def nominal(**kw):
    r = {"timestamp": "2030-01-01T00:00:00Z", "astronaut_id": "SIM-A1", "mission_day": 1, "scenario_id": 0,
         "scenario_label": "Day-1 nominal", "cum_dose_msv": 0, "proton_flux_pfu": 0.1, "flare_active": 0,
         "sleep_h": 7.5, "hrv_rmssd_ms": 60, "hrv_baseline_ms": 60, "fatigue": 2, "stress": 2,
         "loading_index": 100, "loading_target": 100, "balance_score": 95,
         "cabin_o2_pct": 21, "cabin_co2_ppm": 800, "cabin_pressure_kpa": 101.3, "cabin_temp_c": 22,
         "cabin_humidity_pct": 45, "scrubber_state": "nominal", "latency_s": 1.3,
         "open_medical_flags": 0, "source": "SIMULATED"}
    r.update(kw)
    return r


def test_all_nominal():
    a = assess(nominal())
    for d in a["divisions"].values():
        assert d["score"] == 100.0 and d["status"] == "GREEN"
    t = a["total"]
    assert t["score"] == 100.0 and t["grade"] == "A+" and t["status"] == "GREEN"
    assert t["penalty"] == 0 and t["capped"] is False and t["delta_from_day1"] == 0.0


def test_string_inputs_accepted():
    r = {k: (str(v) if not isinstance(v, str) else v) for k, v in nominal(flare_active="1").items()}
    r["flare_active"] = "1"
    assert score_radiation(r)["score"] == 90.0  # 100 - 10 flare


def test_boundaries():
    for s, letter, st in [(100, "A+", "GREEN"), (95, "A+", "GREEN"), (94.9, "A", "GREEN"), (90, "A", "GREEN"),
                          (89.9, "B", "GREEN"), (75, "B", "GREEN"), (74.9, "C", "YELLOW"), (55, "C", "YELLOW"),
                          (54.9, "D", "YELLOW"), (35, "D", "YELLOW"), (34.9, "F", "RED"), (0, "F", "RED")]:
        assert grade_letter(s) == letter and status(s) == st, s
    assert status(None) == "NO_DATA" and grade_letter(None) is None


def test_weights_sum():
    assert abs(sum(DEFAULT_WEIGHTS.values()) - 1.0) < 1e-9
    assert "source" in DEFAULT_CONFIG["radiation"]["career_limit_msv"]


def test_single_division_30_bottleneck():
    # radiation: dose 600 -> -60, flare -10 => 30. weighted = .25*30 + .75*100 = 82.5 -> capped 54.9 (D)
    a = assess(nominal(cum_dose_msv=600, flare_active=1))
    assert a["divisions"]["radiation"]["score"] == 30.0
    t = a["total"]
    assert t["weighted"] == 82.5 and t["penalty"] == 0 and t["capped"] is True
    assert t["score"] == 54.9 and t["grade"] == "D"


def test_three_yellow_penalty():
    # radiation 60 (dose 400 -> -40... use 600 dose -> 40), mental: sleep 4.5 -25, fatigue 10 -20 => 55
    # gravity: ratio .5 -> -30, balance 45 -> -30 (cap) => 40. others 100 (earth tier1)
    a = assess(nominal(cum_dose_msv=600, sleep_h=4.5, fatigue=10, loading_index=50, balance_score=45))
    d = {k: v["score"] for k, v in a["divisions"].items()}
    assert d == {"radiation": 40.0, "mental_health": 55.0, "gravity": 40.0, "life_support": 100.0, "earth_distance": 100.0}
    # weighted = .25*40 + .20*55 + .15*40 + .25*100 + .15*100 = 10+11+6+25+15 = 67 ; penalty -10 -> 57
    t = a["total"]
    assert t["weighted"] == 67.0 and t["penalty"] == -10 and t["score"] == 57.0 and not t["capped"]
    assert t["grade"] == "C"


def test_penalty_and_cap_together():
    # radiation 10 (RED), mental 55, gravity 40: weighted = 2.5+11+6+25+15 = 59.5; -10 = 49.5 (<54.9 so cap no change)
    a = assess(nominal(cum_dose_msv=600, proton_flux_pfu=12, flare_active=1, sleep_h=4.5, fatigue=10,
                       loading_index=50, balance_score=45))
    t = a["total"]
    assert a["divisions"]["radiation"]["score"] == 10.0
    assert t["weighted"] == 59.5 and t["penalty"] == -10 and t["capped"] is True and t["score"] == 49.5
    # cap actually binds: weighted high
    divs = {"radiation": {"score": 20.0, "status": "RED"}, "mental_health": {"score": 70.0, "status": "YELLOW"},
            "gravity": {"score": 70.0, "status": "YELLOW"}, "life_support": {"score": 100.0, "status": "GREEN"},
            "earth_distance": {"score": 100.0, "status": "GREEN"}}
    # weighted = 5+14+10.5+25+15 = 69.5; -10 = 59.5 -> cap 54.9
    t = total_grade(divs)
    assert t["weighted"] == 69.5 and t["score"] == 54.9 and t["capped"] and t["grade"] == "D"


def test_radiation_extreme():
    r = score_radiation(nominal(cum_dose_msv=600, proton_flux_pfu=12, flare_active=1))
    assert r["score"] == 10.0 and r["status"] == "RED" and r["grade"] == "F"
    assert [f["code"] for f in r["factors"]] and all({"code", "label", "value", "deduction"} <= set(f) for f in r["factors"])
    # dose 300 -> 30 deduction; proton 9.9 below threshold
    assert score_radiation(nominal(cum_dose_msv=300, proton_flux_pfu=9.9))["score"] == 70.0
    assert score_radiation(nominal(cum_dose_msv=1200))["score"] == 40.0  # capped at 60


def test_other_division_formulas():
    # sleep 5.5 -15; hrv 45/60 -> 25% drop -25; fatigue 7 -> 8; stress 6 -> 4 => 100-52 = 48
    assert score_mental_health(nominal(sleep_h=5.5, hrv_rmssd_ms=45, fatigue=7, stress=6))["score"] == 48.0
    assert score_mental_health(nominal(hrv_baseline_ms="", hrv_rmssd_ms=10))["score"] == 100.0  # no baseline
    # ratio .7 -> -10 ; balance 75 -> -8 => 82
    assert score_gravity(nominal(loading_index=70, balance_score=75))["score"] == 82.0
    # co2 5500 -> 10; o2 18.5 -> 15; pressure 94 -> 12; scrubber offline 35 => 28
    assert score_life_support(nominal(cabin_co2_ppm=5500, cabin_o2_pct=18.5, cabin_pressure_kpa=94,
                                      scrubber_state="offline"))["score"] == 28.0
    assert score_life_support(nominal(scrubber_state="degraded"))["score"] == 85.0


def test_earth_distance_tier3_conditional():
    # all others green -> no latency deduction
    assert assess(nominal(latency_s=900))["divisions"]["earth_distance"]["score"] == 100.0
    # radiation 40 YELLOW + tier3 -> -30 => 70
    a = assess(nominal(latency_s=900, cum_dose_msv=600))
    assert a["divisions"]["earth_distance"]["score"] == 70.0
    a = assess(nominal(latency_s=30, cum_dose_msv=600))  # tier 2 -> -15
    assert a["divisions"]["earth_distance"]["score"] == 85.0


def test_open_flags_cap():
    assert assess(nominal(open_medical_flags=2))["divisions"]["earth_distance"]["score"] == 90.0
    assert assess(nominal(open_medical_flags="9"))["divisions"]["earth_distance"]["score"] == 80.0  # max -20


def test_no_data_renormalised():
    r = nominal(latency_s="", open_medical_flags="", cum_dose_msv=600)
    a = assess(r)
    assert a["divisions"]["earth_distance"]["status"] == "NO_DATA" and a["divisions"]["earth_distance"]["score"] is None
    # radiation 40, others 100; weights excl earth: .25*40+.25*100+.2*100+.15*100 = 70 / .85 = 82.35 -> 82.4
    assert a["total"]["weighted"] == 82.4
    # entire division null
    r = nominal(cabin_o2_pct="", cabin_co2_ppm="", cabin_pressure_kpa="", scrubber_state="")
    assert assess(r)["divisions"]["life_support"]["status"] == "NO_DATA"


def test_delta_from_day1():
    a = assess(nominal(cum_dose_msv=600), day1_score=100.0)
    assert a["total"]["delta_from_day1"] == a["total"]["score"] - 100.0
    a = assess(nominal(), day1_score=90.0)
    assert a["total"]["delta_from_day1"] == 10.0


def test_assess_label_and_interaction_flags():
    a = assess(nominal(cum_dose_msv=600, sleep_h=4.5, fatigue=10))
    assert a["label"] == "Readiness & Condition Index \u2014 Illustrative screening metric, not a medical diagnosis"
    assert a["astronaut_id"] == "SIM-A1" and a["mission_day"] == 1 and a["source"] == "SIMULATED"
    assert [f["pair"] for f in a["interaction_flags"]] == [["radiation", "mental_health"]]
    assert a["interaction_flags"][0]["label"] == "Hypothesis from HRP hazard descriptions"
    assert assess(nominal())["interaction_flags"] == []
    assert list(a["divisions"]) == ["radiation", "mental_health", "gravity", "life_support", "earth_distance"]
