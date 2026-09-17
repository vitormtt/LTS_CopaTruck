"""Unit tests for the handling-balance analysis (src/analysis/handling_balance.py)."""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analysis.handling_balance import (
    BalanceGeometry,
    balance_metrics,
    geometry_from_params,
    handling_balance,
    roll_stiffness_distribution,
)

_BASE = dict(
    mu=1.6, lf=1.78, lr=1.87, h_cg=1.1, mass=4950.0, cl=0.05, a_front=8.7,
    k_roll_front=115000.0, k_roll_rear=115000.0,
    track_front=2.15, track_rear=2.13, aero_balance=0.5,
)


def _geom(**over) -> BalanceGeometry:
    return BalanceGeometry(**{**_BASE, **over})


def test_rsd_balanced_is_half() -> None:
    assert roll_stiffness_distribution(_geom()) == pytest.approx(0.5)


def test_rsd_front_stiff_above_half() -> None:
    assert roll_stiffness_distribution(_geom(k_roll_front=200000.0)) > 0.5


def test_balance_zero_on_straight() -> None:
    v = np.full(3, 60.0)
    a_lat = np.array([0.0, 0.3, -0.5])  # all below the 1.0 m/s² corner threshold
    ch = handling_balance(a_lat, v, _geom())
    assert np.all(ch.front_utilisation == 0.0)
    assert np.all(ch.rear_utilisation == 0.0)
    assert not np.any(ch.understeer)


def test_balance_positive_utilisation_when_cornering() -> None:
    v = np.array([40.0])
    a_lat = np.array([12.0])  # ~1.2g corner
    ch = handling_balance(a_lat, v, _geom())
    assert ch.front_utilisation[0] > 0.0
    assert ch.rear_utilisation[0] > 0.0


def test_more_front_roll_stiffness_shifts_toward_understeer() -> None:
    # The paper's mechanism: increasing front RSD raises front load transfer,
    # cutting front grip -> higher front utilisation -> more understeer.
    v = np.array([40.0])
    a_lat = np.array([10.0])
    front_stiff = handling_balance(a_lat, v, _geom(k_roll_front=200000.0, k_roll_rear=50000.0))
    rear_stiff = handling_balance(a_lat, v, _geom(k_roll_front=50000.0, k_roll_rear=200000.0))
    assert front_stiff.front_utilisation[0] > rear_stiff.front_utilisation[0]
    assert front_stiff.balance[0] > rear_stiff.balance[0]     # more understeer
    assert front_stiff.understeer[0]                          # front limits


def test_downforce_lowers_utilisation_at_speed() -> None:
    a_lat = np.array([10.0])
    v = np.array([80.0])
    no_aero = handling_balance(a_lat, v, _geom()).front_utilisation[0]
    downforce = handling_balance(a_lat, v, _geom(cl=-0.8)).front_utilisation[0]
    assert downforce < no_aero


def test_balance_metrics_reports_understeer_fraction() -> None:
    v = np.full(3, 40.0)
    a_lat = np.array([10.0, 10.0, 0.0])  # 2 cornering, 1 straight
    ch = handling_balance(a_lat, v, _geom(k_roll_front=200000.0, k_roll_rear=50000.0))
    m = balance_metrics(ch)
    assert m["understeer_fraction"] == pytest.approx(1.0)  # both corner pts understeer
    assert m["peak_front_utilisation"] > 0.0


def test_geometry_from_params_maps_solver_dict() -> None:
    params = {"mu": 1.6, "lf": 1.78, "lr": 1.87, "h_cg": 1.1, "m": 4950.0,
              "Cl": 0.05, "A_front": 8.7, "k_roll_front": 115000.0,
              "k_roll_rear": 115000.0, "track_width_front": 2.15,
              "track_width_rear": 2.13, "aero_balance": 0.5}
    geom = geometry_from_params(params)
    assert geom.k_roll_front == 115000.0
    assert geom.aero_balance == 0.5


def test_shape_mismatch_raises() -> None:
    with pytest.raises(ValueError):
        handling_balance(np.zeros(3), np.zeros(4), _geom())
