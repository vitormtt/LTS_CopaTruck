"""Unit tests for the driver report bundle (src/analysis/driver_report.py)."""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analysis.brake_lockup import geometry_from_params as lockup_geom, lockup_margins
from src.analysis.handling_balance import geometry_from_params as balance_geom, handling_balance
from src.analysis.driver_report import DriverReport, driver_report_from_result

# VW 31320-ish flat solver params (superset of both geometries' required keys)
_PARAMS = {
    "mu": 1.6, "brake_balance": 60.0, "lf": 1.78, "lr": 1.87, "h_cg": 1.1,
    "m": 4950.0, "Cl": 0.0, "A_front": 8.7,
    "k_roll_front": 5.0e5, "k_roll_rear": 4.0e5,
    "track_width_front": 2.0, "track_width_rear": 1.9, "aero_balance": 0.5,
}


def _synthetic_result() -> dict:
    """Half-braking, half-cornering lap trace at constant speed."""
    return {
        "v_profile": np.full(10, 50.0),                      # m/s
        "a_long": np.array([-8.0] * 5 + [0.0] * 5),          # braking then coast
        "a_lat": np.array([0.0] * 5 + [12.0] * 5),           # straight then corner
    }


def test_driver_report_shapes_and_kpi_keys() -> None:
    dr = driver_report_from_result(_synthetic_result(), _PARAMS)
    assert isinstance(dr, DriverReport)
    assert dr.lockup.front_margin.shape == (10,)
    assert dr.balance.balance.shape == (10,)
    assert set(dr.lockup_kpis) == {
        "peak_front_margin", "peak_rear_margin", "near_lockup_fraction"}
    assert set(dr.balance_kpis) == {
        "mean_balance", "understeer_fraction",
        "peak_front_utilisation", "peak_rear_utilisation"}


def test_driver_report_channels_isolate_braking_and_cornering() -> None:
    dr = driver_report_from_result(_synthetic_result(), _PARAMS)
    # Braking half loads the lockup channel, corner half is zero.
    assert np.all(dr.lockup.rear_margin[:5] > 0.0)
    assert np.all(dr.lockup.rear_margin[5:] == 0.0)
    # Cornering half loads the balance channel, braking half is zero.
    assert np.all(dr.balance.front_utilisation[5:] > 0.0)
    assert np.all(dr.balance.front_utilisation[:5] == 0.0)


def test_driver_report_matches_direct_channel_calls() -> None:
    res = _synthetic_result()
    dr = driver_report_from_result(res, _PARAMS)
    lu = lockup_margins(res["v_profile"], res["a_long"], lockup_geom(_PARAMS))
    hb = handling_balance(res["a_lat"], res["v_profile"], balance_geom(_PARAMS))
    np.testing.assert_array_equal(dr.lockup.front_margin, lu.front_margin)
    np.testing.assert_array_equal(dr.lockup.rear_margin, lu.rear_margin)
    np.testing.assert_array_equal(dr.balance.balance, hb.balance)


def test_driver_report_missing_channel_raises_keyerror() -> None:
    res = _synthetic_result()
    del res["a_lat"]
    with pytest.raises(KeyError, match="a_lat"):
        driver_report_from_result(res, _PARAMS)
