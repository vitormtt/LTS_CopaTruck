"""Tests for the design-view curve modules (tire MF + transmission)."""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.vehicle.tire_model import magic_formula, tire_curves
from src.vehicle.transmission_curves import (
    gear_curves,
    resistance_curve,
    speed_kmh_at_rpm,
)

# --- Tire MF -----------------------------------------------------------

_MF = dict(mu=1.2, fz_n=12_000.0, wheel_radius_m=0.52,
           b=10.0, c=1.3, d=1.0, e=0.97)


def test_magic_formula_is_odd_and_peaks_at_d():
    x = np.linspace(-1.0, 1.0, 401)
    y = magic_formula(x, 10.0, 1.3, 5.0, 0.97)
    np.testing.assert_allclose(y, -y[::-1], atol=1e-9)     # odd symmetry
    assert np.max(np.abs(y)) <= 5.0 + 1e-9                 # bounded by D


def test_tire_curves_peak_forces_bounded_by_mu_d_fz():
    tc = tire_curves(**_MF)
    cap = _MF["mu"] * _MF["d"] * _MF["fz_n"]
    # Fx peaks inside the ±0.3 slip-ratio sweep; Fy's true peak sits just
    # past the ±12° sweep (C=1.3 -> α_m ≈ 15°) so it approaches the cap.
    assert np.max(np.abs(tc.fx)) == pytest.approx(cap, rel=0.02)
    assert 0.85 * cap < np.max(np.abs(tc.fy)) <= cap + 1e-6


def test_tire_curves_moments_have_physical_signs():
    tc = tire_curves(**_MF)
    pos = tc.slip_angle_deg > 2.0
    # Positive slip -> positive Fy -> restoring (negative) Mz and Mx
    assert np.all(tc.fy[pos] > 0.0)
    assert np.all(tc.mz[pos] < 0.0)
    assert np.all(tc.mx[pos] < 0.0)
    # Rolling resistance opposes rolling everywhere
    assert np.all(tc.my < 0.0)


def test_tire_curves_rejects_nonpositive_load():
    with pytest.raises(ValueError, match="fz_n"):
        tire_curves(**{**_MF, "fz_n": 0.0})


# --- Transmission ------------------------------------------------------

_ZF6 = dict(gear_ratios=[6.75, 3.60, 2.13, 1.39, 1.00, 0.78],
            final_drive=3.42, wheel_radius_m=0.52,
            torque_curve_rpm=[1000.0, 1300.0, 1900.0, 2300.0],
            torque_curve_nm=[4200.0, 5600.0, 5200.0, 3900.0],
            max_torque_nm=5600.0, rpm_idle=600.0, rpm_max=2300.0,
            driveline_efficiency=0.88)


def test_speed_grows_with_rpm_and_shrinks_with_ratio():
    v_low = speed_kmh_at_rpm(np.array([1500.0]), 6.75, 3.42, 0.52)[0]
    v_high = speed_kmh_at_rpm(np.array([1500.0]), 0.78, 3.42, 0.52)[0]
    assert v_high > v_low > 0.0


def test_gear_curves_cover_increasing_speed_ranges():
    curves = gear_curves(**_ZF6)
    assert len(curves) == 6
    top_speeds = [c.speed_kmh[-1] for c in curves]
    assert top_speeds == sorted(top_speeds)           # each gear reaches higher
    # 6th at rpm_max on 0.52 m wheel ≈ 169 km/h engine-limited
    assert top_speeds[-1] == pytest.approx(169.0, rel=0.02)


def test_tractive_force_decreases_up_the_gearbox():
    curves = gear_curves(**_ZF6)
    peak_forces = [np.max(c.tractive_force_n) for c in curves]
    assert peak_forces == sorted(peak_forces, reverse=True)


def test_flat_torque_fallback_when_curve_missing():
    cfg = {**_ZF6, "torque_curve_rpm": [], "torque_curve_nm": []}
    curves = gear_curves(**cfg)
    f = curves[0].tractive_force_n
    np.testing.assert_allclose(f, f[0])               # flat torque -> flat force


def test_resistance_curve_monotonic_and_positive():
    v, r = resistance_curve(4950.0, 0.74, 8.7, 220.0)
    assert np.all(r > 0.0)
    assert np.all(np.diff(r) > 0.0)                   # drag dominates, rising


# --- Racing line vehicle-width corridor -------------------------------

def test_racing_line_width_narrows_corridor():
    from src.tracks.racing_line import compute_racing_line
    # Circular track, 10 m wide: plenty of corridor for a point, less for a truck
    t = np.linspace(0.0, 2.0 * np.pi, 120, endpoint=False)
    center = np.column_stack([100.0 * np.cos(t), 100.0 * np.sin(t)])
    left = np.column_stack([105.0 * np.cos(t), 105.0 * np.sin(t)])
    right = np.column_stack([95.0 * np.cos(t), 95.0 * np.sin(t)])
    point = compute_racing_line(center, left, right, closed=True)
    truck = compute_racing_line(center, left, right, closed=True,
                                vehicle_width_m=2.5)
    # Truck line must stay strictly inside the point-width envelope
    assert np.max(np.abs(truck.alpha)) < np.max(np.abs(point.alpha))
    assert np.max(np.abs(truck.alpha)) <= 1.0 - (2.5 / 2.0) / 5.0 + 1e-6
