"""
Tests for deriving brake capacity from hardware (Limpert brake-torque chain).

Replaces the magic ``max_brake_force`` slider with a value computed from
caliper/pad/disc geometry, so the deceleration ceiling is physical rather
than hand-tuned.
"""
from __future__ import annotations

import math

import pytest

from src.vehicle.brake_hardware import (
    BrakeHardware,
    axle_brake_force,
    brake_force_from_hardware,
)


def _typical_axle() -> BrakeHardware:
    # Order-of-magnitude heavy-truck disc brake (values are placeholders
    # pending real Copa Truck data — see docs/research prompt).
    return BrakeHardware(
        n_pistons=4,
        piston_diameter_m=0.060,     # 60 mm pistons
        line_pressure_bar=100.0,     # ~100 bar peak hydraulic
        pad_friction=0.40,           # organic/sintered pad μ
        disc_effective_radius_m=0.18,
        wheel_radius_m=0.52,
    )


def test_axle_brake_force_matches_limpert_chain():
    hw = _typical_axle()
    piston_area = math.pi * (hw.piston_diameter_m / 2.0) ** 2
    clamp = hw.line_pressure_bar * 1e5 * piston_area * hw.n_pistons
    # two friction faces per disc
    torque = 2.0 * hw.pad_friction * clamp * hw.disc_effective_radius_m
    expected = torque / hw.wheel_radius_m
    assert axle_brake_force(hw) == pytest.approx(expected)


def test_total_force_sums_axles():
    front = _typical_axle()
    rear = _typical_axle()
    total = brake_force_from_hardware(front, rear)
    assert total == pytest.approx(axle_brake_force(front) + axle_brake_force(rear))


def test_higher_line_pressure_increases_force():
    lo = _typical_axle()
    hi = BrakeHardware(**{**lo.__dict__, "line_pressure_bar": 150.0})
    assert axle_brake_force(hi) > axle_brake_force(lo)


def test_force_is_positive_and_finite():
    f = brake_force_from_hardware(_typical_axle(), _typical_axle())
    assert f > 0.0 and math.isfinite(f)


def test_zero_pressure_gives_zero_force():
    hw = BrakeHardware(**{**_typical_axle().__dict__, "line_pressure_bar": 0.0})
    assert axle_brake_force(hw) == pytest.approx(0.0)


def test_invalid_wheel_radius_raises():
    with pytest.raises(ValueError, match="wheel_radius"):
        axle_brake_force(BrakeHardware(**{**_typical_axle().__dict__,
                                          "wheel_radius_m": 0.0}))


def test_deceleration_in_physical_range_for_truck():
    # Sanity: a ~5 t truck on these placeholder numbers should brake in a
    # plausible band (grip-limited in reality, but the hardware ceiling
    # must not be absurdly low/high).
    force = brake_force_from_hardware(_typical_axle(), _typical_axle())
    decel = force / 4950.0
    assert 3.0 < decel < 25.0
