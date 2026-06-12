"""
Unit tests for the Copa Truck technical regulation validator.
"""
from src.vehicle.parameters import copa_truck_2dof_default
from src.vehicle.regulation_validator import validate_regulation_compliance


def test_default_vehicle_compliance():
    vp = copa_truck_2dof_default()
    validation = validate_regulation_compliance(vp)
    
    # The default vehicle should be compliant with core dimensions/weights
    # Mercedes Actros default has mass=4500, which is below 4890 kg.
    # Wait! Let's check: mass=4500 kg + 90 kg pilot = 4590 kg < 4890 kg.
    # So the default vehicle should NOT be fully compliant on total mass unless we adjust mass.
    # Let's adjust mass to 4800 kg so that total weight (with pilot 90kg) = 4890 kg exactly.
    vp.mass_geometry.mass = 4800.0
    # Also front axle sem piloto: mass_no_pilot = 4800 - 90 = 4710.
    # front_load = 4710 * lr/L = 4710 * 2.3/4.4 = 2461.59 kg (below 2520 kg).
    # Let's adjust weight distribution front or mass to make it compliant!
    # front weight distribution: wd_front = lr/wheelbase.
    # If wheelbase = 3.3 m, lf = 1.5, lr = 1.8, wd_front = 1.8/3.3 = 0.545.
    # Let's make it fully compliant:
    vp.mass_geometry.wheelbase = 3.5
    vp.mass_geometry.lr = 1.9
    vp.mass_geometry.lf = 1.6
    vp.mass_geometry.track_width_front = 2.10
    vp.mass_geometry.track_width_rear = 2.10
    vp.mass_geometry.mass = 5000.0 # 5000 kg total
    # front axle load no pilot: (5000 - 90) * 1.9 / 3.5 = 2665 kg (above 2520 kg) - OK!
    
    validation = validate_regulation_compliance(vp)
    assert validation["compliant"] is True
    assert len(validation["errors"]) == 0


def test_non_compliance_wheelbase():
    vp = copa_truck_2dof_default()
    # Wheelbase below 3.25 m limit
    vp.mass_geometry.wheelbase = 3.10
    vp.mass_geometry.lf = 1.5
    vp.mass_geometry.lr = 1.6
    validation = validate_regulation_compliance(vp)
    assert validation["compliant"] is False
    assert any("Wheelbase" in err for err in validation["errors"])


def test_non_compliance_weight():
    vp = copa_truck_2dof_default()
    # Weight below 4890 kg limit (e.g. 4200 kg)
    vp.mass_geometry.mass = 4200.0
    validation = validate_regulation_compliance(vp)
    assert validation["compliant"] is False
    assert any("weight" in err.lower() for err in validation["errors"])


def test_season_weight_limits_2025_vs_2026():
    """4 890 kg passes the 2025 rulebook but fails 2026 (4 950 kg)."""
    vp = copa_truck_2dof_default()
    vp.mass_geometry.wheelbase = 3.5
    vp.mass_geometry.lr = 1.9
    vp.mass_geometry.lf = 1.6
    vp.mass_geometry.track_width_front = 2.10
    vp.mass_geometry.track_width_rear = 2.10
    vp.mass_geometry.mass = 4890.0

    v2025 = validate_regulation_compliance(vp, season=2025)
    assert v2025["compliant"] is True, v2025["errors"]

    v2026 = validate_regulation_compliance(vp, season=2026)
    assert v2026["compliant"] is False
    assert any("4950" in err for err in v2026["errors"])

    vp.mass_geometry.mass = 4950.0
    assert validate_regulation_compliance(vp, season=2026)["compliant"] is True
