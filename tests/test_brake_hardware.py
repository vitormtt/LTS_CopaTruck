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
    # two friction faces per disc, one caliper per wheel
    torque = 2.0 * hw.pad_friction * clamp * hw.disc_effective_radius_m
    expected = torque / hw.wheel_radius_m * hw.wheels_per_axle
    assert axle_brake_force(hw) == pytest.approx(expected)


def test_wheels_per_axle_scales_force():
    per_axle = _typical_axle()                       # default: 2 wheels
    per_wheel = BrakeHardware(**{**per_axle.__dict__, "wheels_per_axle": 1})
    assert axle_brake_force(per_axle) == pytest.approx(
        2.0 * axle_brake_force(per_wheel))


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
    # Sanity: the hardware CEILING of a race-truck air-disc system is
    # massively oversized vs tyre grip — ~5.5 g documented for the real
    # Copa Truck package (docs/Especificações Freio Copa Truck.md §8).
    # It must be well above grip (~1.5 g) but not absurd (>8 g).
    force = brake_force_from_hardware(_typical_axle(), _typical_axle())
    decel = force / 4950.0
    assert 15.0 < decel < 80.0


# --- VehicleParams wiring (preset -> derived max_brake_force) ---

_HW_FRONT = {"n_pistons": 2, "piston_diameter_m": 0.068,
             "line_pressure_bar": 314.0, "pad_friction": 0.48,
             "disc_effective_radius_m": 0.1725}
_HW_REAR = {**_HW_FRONT, "line_pressure_bar": 263.0}


def _default_params():
    from src.vehicle.parameters import VehicleParams
    return VehicleParams.from_solver_dict({})


def _params_with_hardware():
    vp = _default_params()
    vp.tire.wheel_radius = 0.52
    vp.brake.hardware_front = dict(_HW_FRONT)
    vp.brake.hardware_rear = dict(_HW_REAR)
    return vp


def test_derived_brake_force_matches_researched_package():
    # Knorr SN7 + Fras-le PD/116 package: ~5.5 g ceiling on 4950 kg
    # (docs/Especificações Freio Copa Truck.md §8-9).
    vp = _params_with_hardware()
    assert vp.derived_brake_force() == pytest.approx(266_932.0, rel=1e-3)


def test_solver_dict_overrides_max_brake_force_when_hardware_present():
    vp = _params_with_hardware()
    assert vp.to_solver_dict()["max_brake_force"] == pytest.approx(
        vp.derived_brake_force())


def test_solver_dict_falls_back_without_hardware():
    vp = _default_params()
    assert vp.derived_brake_force() is None
    assert vp.to_solver_dict()["max_brake_force"] == vp.brake.max_brake_force


def test_hardware_roundtrips_through_solver_dict():
    from src.vehicle.parameters import VehicleParams
    vp = _params_with_hardware()
    back = VehicleParams.from_solver_dict(vp.to_solver_dict())
    assert back.brake.hardware_front == _HW_FRONT
    assert back.brake.hardware_rear == _HW_REAR
    assert back.derived_brake_force() == pytest.approx(vp.derived_brake_force())


def test_validation_rejects_partial_hardware():
    from src.vehicle.parameters import validate_vehicle_params
    vp = _params_with_hardware()
    vp.brake.hardware_rear = None
    errors = validate_vehicle_params(vp)
    assert any("BOTH front and rear" in e for e in errors)

    vp2 = _params_with_hardware()
    del vp2.brake.hardware_front["pad_friction"]
    errors2 = validate_vehicle_params(vp2)
    assert any("missing keys" in e for e in errors2)
