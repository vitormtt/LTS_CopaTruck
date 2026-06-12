"""
Round-trip tests for the relational vehicle mapping (no database needed):
flat solver dict -> per-table rows -> flat dict must preserve every
physical parameter the solver consumes.
"""

import pytest

from src.database.vehicle_mapping import (
    FLAT_TO_TABLES,
    decompose_params,
    recompose_params,
)
from src.vehicle.fleet import get_vehicle_by_id
from src.vehicle.parameters import VehicleParams


def _roundtrip(params: dict) -> dict:
    tables, gears, torque = decompose_params(params)
    return recompose_params(tables, gears, torque)


def test_roundtrip_preserves_all_mapped_keys():
    vp = get_vehicle_by_id("volkswagen_31320")
    params = vp.to_solver_dict()
    back = _roundtrip(params)

    for table_map in FLAT_TO_TABLES.values():
        for flat_key in table_map:
            if flat_key in params and params[flat_key] is not None:
                assert back[flat_key] == pytest.approx(params[flat_key]), flat_key

    assert back["gear_ratios"] == pytest.approx(params["gear_ratios"])
    assert back["n_gears"] == params["n_gears"]
    assert back["torque_curve_rpm"] == pytest.approx(params["torque_curve_rpm"])
    assert back["torque_curve_nm"] == pytest.approx(params["torque_curve_nm"])
    assert back["track_width"] == pytest.approx(
        (params["track_width_front"] + params["track_width_rear"]) / 2.0
    )


def test_roundtrip_rebuilds_equivalent_vehicle():
    """from_solver_dict(roundtrip(to_solver_dict(vp))) must equal vp physically."""
    vp = get_vehicle_by_id("scania_r480")
    back = _roundtrip(vp.to_solver_dict())
    back["name"] = vp.name
    rebuilt = VehicleParams.from_solver_dict(back)

    assert rebuilt.mass_geometry.mass == pytest.approx(vp.mass_geometry.mass)
    assert rebuilt.mass_geometry.wheelbase == pytest.approx(vp.mass_geometry.wheelbase)
    assert rebuilt.tire.friction_coefficient == pytest.approx(vp.tire.friction_coefficient)
    assert rebuilt.engine.max_power == pytest.approx(vp.engine.max_power)
    assert rebuilt.transmission.gear_ratios == pytest.approx(vp.transmission.gear_ratios)
    assert rebuilt.transmission.final_drive_ratio == pytest.approx(
        vp.transmission.final_drive_ratio
    )
    assert rebuilt.brake.brake_balance == pytest.approx(vp.brake.brake_balance)
    assert rebuilt.aero.drag_coefficient == pytest.approx(vp.aero.drag_coefficient)
    assert rebuilt.engine.torque_curve_nm == pytest.approx(vp.engine.torque_curve_nm)


def test_torque_curve_recomposed_in_rpm_order():
    params = {"torque_curve_rpm": [2000.0, 800.0, 3500.0],
              "torque_curve_nm": [4000.0, 1500.0, 2500.0],
              "mu": 1.5, "r_wheel": 0.65}
    back = _roundtrip(params)
    assert back["torque_curve_rpm"] == [800.0, 2000.0, 3500.0]
    assert back["torque_curve_nm"] == [1500.0, 4000.0, 2500.0]


def test_empty_lists_do_not_emit_keys():
    back = _roundtrip({"mu": 1.5, "r_wheel": 0.65})
    assert "gear_ratios" not in back
    assert "torque_curve_rpm" not in back
