"""
Tests for the bias-limited deceleration model.

Verifies the coupling between front brake bias and longitudinal load
transfer introduced in _bias_limited_decel() (Limpert 1999, ch. 7).
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.simulation.lap_time_solver import (  # noqa: E402
    _LegacyVehicleParams,
    _bias_limited_decel,
)

G = 9.81


def _make_params(**overrides) -> _LegacyVehicleParams:
    """Default truck-like flat params for the helper under test."""
    defaults = dict(
        m=5000.0, lf=2.1, lr=2.3, h_cg=1.1, mu=1.1,
        brake_balance=58.0, max_brake_force=60000.0, max_decel=9.5,
    )
    defaults.update(overrides)
    return _LegacyVehicleParams(**defaults)


def _ideal_bias_pct(p: _LegacyVehicleParams, mu: float) -> float:
    """Bias matching the dynamic front load share at the lock-up point.

    With ideal bias both axles lock simultaneously at a = mu * g:
    front load share = (lr + mu*h_cg) / L.
    """
    return 100.0 * (p.lr + mu * p.h_cg) / p.L


def test_ideal_bias_maximises_decel() -> None:
    """The ideal bias must yield deceleration >= any other bias."""
    p = _make_params(max_brake_force=1e9, max_decel=1e9)
    mu = p.mu
    m = p.m
    f_normal = m * G

    p.brake_balance = _ideal_bias_pct(p, mu)
    a_ideal = _bias_limited_decel(p, mu, m, f_normal)

    # Ideal bias reaches the full friction-limited deceleration mu*g
    assert np.isclose(a_ideal, mu * G, rtol=1e-6)

    for bias in np.arange(30.0, 85.0, 2.5):
        p.brake_balance = bias
        assert _bias_limited_decel(p, mu, m, f_normal) <= a_ideal + 1e-9


def test_extreme_front_bias_degrades_decel() -> None:
    """90% front bias must brake worse than a near-ideal bias."""
    p = _make_params(max_brake_force=1e9)
    mu = p.mu
    f_normal = p.m * G

    p.brake_balance = _ideal_bias_pct(p, mu)
    a_good = _bias_limited_decel(p, mu, p.m, f_normal)

    p.brake_balance = 90.0
    a_bad = _bias_limited_decel(p, mu, p.m, f_normal)

    assert a_bad < a_good * 0.95


def test_brake_force_cap_respected() -> None:
    """A small max_brake_force must cap deceleration at F/m."""
    p = _make_params(max_brake_force=10000.0)
    a = _bias_limited_decel(p, p.mu, p.m, p.m * G)
    assert a <= p.max_brake_force / p.m + 1e-9


def test_downforce_raises_bias_limit() -> None:
    """Higher normal force (downforce) raises the lock-up limit."""
    p = _make_params(max_brake_force=1e9)
    f_static = p.m * G
    a_no_df = _bias_limited_decel(p, p.mu, p.m, f_static)
    a_with_df = _bias_limited_decel(p, p.mu, p.m, f_static * 1.2)
    assert a_with_df > a_no_df
