"""
Tests for the "save as new model" flow: solver-dict round-trip fidelity
for regulation-relevant fields, id slug normalization and the
regulation-compliant VW 31320 copy used as the UI test vehicle.
"""

import pytest

from src.vehicle.fleet import get_vehicle_by_id
from src.vehicle.parameters import VehicleParams
from src.vehicle.regulation_validator import validate_regulation_compliance
from src.visualization.components.vehicle_params import _slugify_model_id


def _make_compliant_vw_copy() -> VehicleParams:
    """VW 31320 with geometry adjusted to pass the CBA regulation checks."""
    vp = get_vehicle_by_id("volkswagen_31320")
    mg = vp.mass_geometry
    mg.mass = 4890.0           # >= 4890 kg minimum with pilot
    mg.lf = 1.65
    mg.lr = 1.95               # (4890-90) * (1.95/3.6) = 2600 kg front >= 2520
    mg.wheelbase = 3.60        # within 3.25-3.85 m window
    mg.track_width_front = 2.14  # outer = 2.455 m <= 2.465 m limit
    mg.track_width_rear = 2.14
    return vp


def test_base_vw_31320_is_non_compliant():
    vp = get_vehicle_by_id("volkswagen_31320")
    result = validate_regulation_compliance(vp)
    assert not result["compliant"]
    assert len(result["errors"]) >= 4  # mass, front axle, wheelbase, widths


def test_compliant_copy_passes_validator():
    vp = _make_compliant_vw_copy()
    result = validate_regulation_compliance(vp)
    assert result["compliant"], f"unexpected errors: {result['errors']}"


def test_solver_dict_round_trip_preserves_regulation_fields():
    original = _make_compliant_vw_copy()
    data = original.to_solver_dict()
    data["name"] = "VW 31320 (Cup Spec Test)"
    data["manufacturer"] = "Volkswagen"
    data["year"] = 2024
    restored = VehicleParams.from_solver_dict(data)

    mg_orig, mg_back = original.mass_geometry, restored.mass_geometry
    assert mg_back.mass == pytest.approx(mg_orig.mass)
    assert mg_back.wheelbase == pytest.approx(mg_orig.wheelbase)
    assert mg_back.lf == pytest.approx(mg_orig.lf)
    assert mg_back.lr == pytest.approx(mg_orig.lr)
    assert mg_back.track_width_front == pytest.approx(mg_orig.track_width_front)
    assert mg_back.track_width_rear == pytest.approx(mg_orig.track_width_rear)
    assert restored.name == "VW 31320 (Cup Spec Test)"

    result = validate_regulation_compliance(restored)
    assert result["compliant"], f"round-trip broke compliance: {result['errors']}"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("VW 31320 (Cup Spec Test)", "vw_31320_cup_spec_test"),
        ("  Scania---R480 Évo  ", "scania_r480_vo"),
        ("___", ""),
        ("Volvo FH16", "volvo_fh16"),
    ],
)
def test_slugify_model_id(raw, expected):
    assert _slugify_model_id(raw) == expected
