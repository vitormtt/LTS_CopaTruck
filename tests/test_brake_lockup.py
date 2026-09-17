"""Unit tests for the brake-lockup analysis (src/analysis/brake_lockup.py)."""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analysis.brake_lockup import (
    LockupGeometry,
    axle_lock_decels,
    geometry_from_params,
    lockup_margins,
    lockup_metrics,
)

# VW 31320-ish geometry for tests
_GEOM = LockupGeometry(
    mu=1.6, brake_balance_pct=60.0, lf=1.78, lr=1.87, h_cg=1.1,
    mass=4950.0, cl=0.0, a_front=8.7,
)


def test_axle_lock_decels_matches_limpert_hand_calc() -> None:
    a_front, a_rear = axle_lock_decels(1.6, 9.81, 0.6, 1.78, 1.87, 1.1)
    assert a_rear == pytest.approx(8.677, abs=1e-2)
    assert a_front == pytest.approx(68.26, abs=1e-1)


def test_axle_lock_decels_front_never_locks_when_bias_below_transfer() -> None:
    # b <= mu*h_cg/L (0.482) -> front axle cannot lock at any deceleration
    a_front, a_rear = axle_lock_decels(1.6, 9.81, 0.40, 1.78, 1.87, 1.1)
    assert a_front == float("inf")
    assert np.isfinite(a_rear)


def test_lockup_margins_zero_when_not_braking() -> None:
    v = np.full(3, 50.0)
    a_long = np.array([0.0, 2.5, -0.0])  # coasting / accelerating only
    ch = lockup_margins(v, a_long, _GEOM)
    assert np.all(ch.front_margin == 0.0)
    assert np.all(ch.rear_margin == 0.0)
    assert not np.any(ch.front_limited)


def test_lockup_margins_rear_at_unity_when_braking_at_rear_limit() -> None:
    v = np.array([50.0])
    a_long = np.array([-8.677])  # exactly the rear-lock decel (cl=0 -> g_eff=g)
    ch = lockup_margins(v, a_long, _GEOM)
    assert ch.rear_margin[0] == pytest.approx(1.0, abs=1e-3)
    assert ch.front_margin[0] == pytest.approx(8.677 / 68.26, abs=1e-2)
    assert not ch.front_limited[0]           # rear locks first at 60% front bias
    assert ch.slip_estimate[0] == pytest.approx(0.15, abs=1e-3)


def test_lockup_margins_more_front_bias_raises_front_margin() -> None:
    v = np.array([50.0])
    a_long = np.array([-6.0])
    front_heavy = LockupGeometry(**{**_GEOM.__dict__, "brake_balance_pct": 75.0})
    rear_heavy = LockupGeometry(**{**_GEOM.__dict__, "brake_balance_pct": 55.0})
    m_front = lockup_margins(v, a_long, front_heavy).front_margin[0]
    m_rear = lockup_margins(v, a_long, rear_heavy).front_margin[0]
    assert m_front > m_rear                  # more front bias -> front closer to lock


def test_lockup_margins_downforce_lowers_margin_at_speed() -> None:
    # cl < 0 (downforce) raises F_normal -> higher lock decel -> lower margin
    v = np.array([80.0])
    a_long = np.array([-8.0])
    no_aero = lockup_margins(v, a_long, _GEOM).rear_margin[0]
    downforce = LockupGeometry(**{**_GEOM.__dict__, "cl": -0.6})
    with_df = lockup_margins(v, a_long, downforce).rear_margin[0]
    assert with_df < no_aero


def test_lockup_metrics_counts_near_lockup_fraction() -> None:
    v = np.full(4, 50.0)
    a_long = np.array([-8.677, -8.677, -1.0, 3.0])  # 2 at limit, 1 light, 1 accel
    ch = lockup_margins(v, a_long, _GEOM)
    m = lockup_metrics(ch, near_lock=0.95)
    assert m["peak_rear_margin"] == pytest.approx(1.0, abs=1e-3)
    # 3 braking points, 2 near lockup -> 2/3
    assert m["near_lockup_fraction"] == pytest.approx(2.0 / 3.0, abs=1e-6)


def test_lockup_margins_shape_mismatch_raises() -> None:
    with pytest.raises(ValueError):
        lockup_margins(np.zeros(3), np.zeros(4), _GEOM)


def test_geometry_from_params_maps_solver_dict() -> None:
    params = {"mu": 1.6, "brake_balance": 60.0, "lf": 1.78, "lr": 1.87,
              "h_cg": 1.1, "m": 4950.0, "Cl": 0.05, "A_front": 8.7}
    geom = geometry_from_params(params)
    assert geom.mu == 1.6
    assert geom.brake_balance_pct == 60.0
    assert geom.mass == 4950.0
    assert geom.a_front == 8.7
