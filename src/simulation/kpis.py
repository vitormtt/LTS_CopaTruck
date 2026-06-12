"""
KPI extraction from a legacy solver result dict.

Pure module (no streamlit, no I/O): the UI layers call compute_kpis()
and hand the result to db_manager.save_simulation_result so every run
is persisted with the exact aggregate schema of the simulation_results
table — the base for cross-referencing runs (driver/team comparisons,
calibration history, solver regression over time).
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np

_G = 9.81
_WOT_THROTTLE_PCT = 99.0    # wide-open-throttle threshold [%]
_BRAKING_BRAKE_PCT = 1.0    # braking threshold [%]


def compute_kpis(result: Dict[str, Any]) -> Dict[str, float]:
    """Aggregate a legacy solver result dict into simulation_results KPIs.

    Time-percentage channels are weighted by the per-sample time step —
    samples are distance-spaced, so counting them would over-weight the
    slow corners.
    """
    v_ms = np.asarray(result["v_profile"], dtype=float)
    a_long = np.asarray(result["a_long"], dtype=float)
    a_lat = np.asarray(result["a_lat"], dtype=float)
    t = np.asarray(result["time"], dtype=float)
    throttle = np.asarray(result["throttle_pct"], dtype=float)
    brake = np.asarray(result["brake_pct"], dtype=float)

    dt = np.diff(t, prepend=t[0])
    total_t = max(float(dt.sum()), 1e-9)

    return {
        "lap_time": float(result["lap_time"]),
        "avg_speed_kmh": float(np.mean(v_ms) * 3.6),
        "max_speed_kmh": float(np.max(v_ms) * 3.6),
        "peak_lat_g": float(np.max(np.abs(a_lat)) / _G),
        "peak_brake_g": float(max(-np.min(a_long), 0.0) / _G),
        "peak_accel_g": float(max(np.max(a_long), 0.0) / _G),
        "time_wot_pct": float(dt[throttle >= _WOT_THROTTLE_PCT].sum() / total_t * 100.0),
        "time_braking_pct": float(dt[brake > _BRAKING_BRAKE_PCT].sum() / total_t * 100.0),
        "fuel_total_l": float(result["consumo"][-1]),
        "final_tyre_temp_c": float(result["temp_pneu"][-1]),
        "final_tyre_pressure_bar": float(result["pressao_pneu"][-1]),
    }
