"""Unit tests for the pure KPI aggregation used by the simulation history."""

import numpy as np
import pytest

from src.simulation.kpis import compute_kpis


def _synthetic_result():
    # 4 samples: accelerating, WOT cruise, braking, corner
    return {
        "lap_time": 10.0,
        "v_profile": np.array([10.0, 20.0, 30.0, 15.0]),       # m/s
        "a_long": np.array([3.0, 0.5, -6.0, 0.0]),             # m/s^2
        "a_lat": np.array([0.5, 1.0, 2.0, 12.0]),              # m/s^2
        "time": np.array([0.0, 2.0, 6.0, 10.0]),               # s
        "throttle_pct": np.array([100.0, 100.0, 0.0, 50.0]),
        "brake_pct": np.array([0.0, 0.0, 80.0, 0.0]),
        "consumo": np.array([0.0, 0.5, 1.0, 1.4]),             # L
        "temp_pneu": np.array([40.0, 55.0, 63.0, 70.0]),       # degC
        "pressao_pneu": np.array([1.8, 1.9, 2.0, 2.05]),       # bar
    }


def test_compute_kpis_aggregates():
    k = compute_kpis(_synthetic_result())
    assert k["lap_time"] == pytest.approx(10.0)
    assert k["max_speed_kmh"] == pytest.approx(30.0 * 3.6)
    assert k["avg_speed_kmh"] == pytest.approx(np.mean([10, 20, 30, 15]) * 3.6)
    assert k["peak_lat_g"] == pytest.approx(12.0 / 9.81)
    assert k["peak_brake_g"] == pytest.approx(6.0 / 9.81)
    assert k["peak_accel_g"] == pytest.approx(3.0 / 9.81)
    assert k["fuel_total_l"] == pytest.approx(1.4)
    assert k["final_tyre_temp_c"] == pytest.approx(70.0)
    assert k["final_tyre_pressure_bar"] == pytest.approx(2.05)


def test_time_percentages_are_dt_weighted():
    k = compute_kpis(_synthetic_result())
    # dt = [0, 2, 4, 4]; WOT on samples 0+1 -> 2s of 10s; braking on sample 2 -> 4s
    assert k["time_wot_pct"] == pytest.approx(20.0)
    assert k["time_braking_pct"] == pytest.approx(40.0)


def test_no_negative_peaks_on_coasting_lap():
    r = _synthetic_result()
    r["a_long"] = np.array([0.0, 0.0, 0.0, 0.0])
    k = compute_kpis(r)
    assert k["peak_brake_g"] == 0.0
    assert k["peak_accel_g"] == 0.0
