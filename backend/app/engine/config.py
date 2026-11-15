"""Engine configuration: thresholds and coefficients with source notes."""
_ILL = "illustrative default"

DEFAULT_CONFIG = {
    "radiation": {
        "career_limit_msv": {"value": 600, "source": "PLAN section 6.1 (career dose ~600 mSv reference); " + _ILL},
        "max_dose_deduction": {"value": 60, "source": _ILL},
        "proton_flux_pfu": {"value": 10, "source": "NOAA S1 solar radiation storm threshold (>=10 pfu)"},
        "proton_deduction": {"value": 20, "source": _ILL},
        "flare_deduction": {"value": 10, "source": _ILL},
    },
    "mental_health": {
        "sleep_low_h": {"value": 6, "source": "PLAN section 6.2; " + _ILL},
        "sleep_low_deduction": {"value": 15, "source": _ILL},
        "sleep_severe_h": {"value": 5, "source": _ILL},
        "sleep_severe_deduction": {"value": 25, "source": _ILL},
        "hrv_max_deduction": {"value": 30, "source": _ILL},
        "fatigue_free": {"value": 5, "source": _ILL},
        "fatigue_coeff": {"value": 4, "source": _ILL},
        "stress_free": {"value": 5, "source": _ILL},
        "stress_coeff": {"value": 4, "source": _ILL},
    },
    "gravity": {
        "loading_ratio_min": {"value": 0.8, "source": "PLAN section 6.2 (80% of target)"},
        "loading_coeff": {"value": 100, "source": _ILL},
        "loading_max_deduction": {"value": 40, "source": _ILL},
        "balance_min": {"value": 85, "source": _ILL},
        "balance_coeff": {"value": 0.8, "source": _ILL},
        "balance_max_deduction": {"value": 30, "source": _ILL},
    },
    "life_support": {
        "co2_ppm_max": {"value": 5000, "source": "PLAN section 6.2 (CO2 > 5,000 ppm); " + _ILL},
        "co2_per_ppm": {"value": 50, "source": _ILL},
        "co2_max_deduction": {"value": 40, "source": _ILL},
        "o2_min_pct": {"value": 19.5, "source": _ILL},
        "o2_max_pct": {"value": 23.5, "source": _ILL},
        "o2_coeff": {"value": 15, "source": _ILL},
        "o2_max_deduction": {"value": 30, "source": _ILL},
        "pressure_min_kpa": {"value": 97, "source": _ILL},
        "pressure_max_kpa": {"value": 103, "source": _ILL},
        "pressure_coeff": {"value": 4, "source": _ILL},
        "pressure_max_deduction": {"value": 20, "source": _ILL},
        "scrubber_degraded_deduction": {"value": 15, "source": _ILL},
        "scrubber_offline_deduction": {"value": 35, "source": _ILL},
    },
    "earth_distance": {
        "tier1_latency_lt_s": {"value": 2, "source": _ILL},
        "tier2_latency_max_s": {"value": 60, "source": _ILL},
        "tier2_deduction": {"value": 15, "source": _ILL},
        "tier3_deduction": {"value": 30, "source": _ILL},
        "flag_deduction": {"value": 5, "source": _ILL},
        "flag_max_deduction": {"value": 20, "source": _ILL},
    },
    "status": {
        "green_min": {"value": 75, "source": "PLAN section 6.3"},
        "yellow_min": {"value": 35, "source": "PLAN section 6.3"},
    },
    "grade": {
        "a_plus_min": {"value": 95, "source": _ILL},
        "a_min": {"value": 90, "source": "PLAN section 6.3"},
        "b_min": {"value": 75, "source": "PLAN section 6.3"},
        "c_min": {"value": 55, "source": "PLAN section 6.3"},
        "d_min": {"value": 35, "source": "PLAN section 6.3"},
    },
    "total": {
        "compound_count": {"value": 3, "source": "PLAN section 6.3"},
        "compound_penalty": {"value": -10, "source": "PLAN section 6.3"},
        "bottleneck_below": {"value": 35, "source": "PLAN section 6.3"},
        "bottleneck_cap": {"value": 54.9, "source": "PLAN section 6.3 (cannot exceed Grade D)"},
    },
}

DEFAULT_WEIGHTS = {
    "radiation": 0.25,
    "life_support": 0.25,
    "mental_health": 0.20,
    "gravity": 0.15,
    "earth_distance": 0.15,
}
