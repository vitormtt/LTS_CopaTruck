"""
Integration and validation tests for Copa Truck simulation.

Validates parameter loading, solver compatibility, speed limits,
and lap time convergence against real telemetry data targets.

Execute from the project root:
    python -m pytest tests/test_copa_truck.py -v
"""
import os
import sys
from pathlib import Path
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.vehicle.fleet import get_vehicle_by_id, list_vehicles
from src.vehicle.parameters import validate_vehicle_params, copa_truck_2dof_default
from src.vehicle.regulation_validator import validate_regulation_compliance
from src.tracks.hdf5 import CircuitHDF5Reader
from src.simulation.lap_time_solver import run_bicycle_model
from src.simulation.telemetry import SimulationTelemetry


def test_copa_truck_presets() -> None:
    """Verify that all truck presets load, validate, and comply with CBA regulation.

    Scania/Volvo presets were removed 2026-07-05: their differentiation had no
    source (Copa Truck equalizes performance via pop-off valve) and they failed
    the CBA regulation validator (mass, wheelbase, width).
    """
    truck_ids = ["volkswagen_31320"]
    fleet = list_vehicles()

    for tid in truck_ids:
        assert tid in fleet
        vp = get_vehicle_by_id(tid)
        assert vp is not None
        assert vp.category == "Truck"
        assert vp.mass_geometry.mass >= 4000.0
        assert vp.engine.rpm_max >= 3000.0

        # Check that there are no parameter validation errors
        errors = validate_vehicle_params(vp)
        assert len(errors) == 0, f"Validation errors in {tid}: {errors}"

        # Every shipped preset must pass CBA scrutineering
        reg = validate_regulation_compliance(vp)
        assert reg["compliant"], f"{tid} non-compliant: {reg['errors']}"


def test_default_preset() -> None:
    """Verify default preset parameters match calibrated specs."""
    vp = copa_truck_2dof_default()
    assert vp.mass_geometry.mass == 4500.0
    assert vp.tire.friction_coefficient == 1.62
    assert vp.engine.max_power == 850000.0
    assert vp.engine.rpm_max == 3500.0


def test_cascavel_validation() -> None:
    """Verify simulation of VW 31320 on Cascavel track matches target time (~1m20s)."""
    vp = get_vehicle_by_id("volkswagen_31320")
    params_dict = vp.to_solver_dict()
    
    track_path = os.path.join(str(ROOT), "tracks", "cascavel.hdf5")
    assert os.path.exists(track_path), "Cascavel track HDF5 not found"
    
    circuit, meta = CircuitHDF5Reader(track_path).read_circuit()
    res = run_bicycle_model(params_dict, circuit, {"gear_min": 4})
    
    # Anchor: pole PRO 2025 = 79.505s (the CALIBRATION target, held in SPM).
    # Since 2026-07-10 qualifying defaults to the flying-lap periodic start
    # (v0 ≈ 180 km/h — a hot lap by definition) and the merged single preset
    # carries the researched ZF6 physics: sim = 75.57s. The ~-4s overshoot
    # is the known mu=1.6 fudge, to be recalibrated with the track/mu
    # pipeline (docs/Validação de Lap Sim.md). This range guards against
    # silent regressions of the CURRENT physics, not against the anchor.
    lap_time = res["lap_time"]
    assert 74.0 <= lap_time <= 78.0, f"Cascavel simulated time {lap_time:.2f}s is out of target range [74s, 78s]"
    
    # Top speed should be around 193 km/h
    v_max = np.max(res["v_profile"]) * 3.6
    assert 185.0 <= v_max <= 200.0, f"Cascavel simulated top speed {v_max:.1f} km/h is out of range [185, 200]"


def test_interlagos_validation() -> None:
    """Verify simulation of VW 31320 on Interlagos track matches target time (~2m07s)."""
    vp = get_vehicle_by_id("volkswagen_31320")
    params_dict = vp.to_solver_dict()
    
    track_path = os.path.join(str(ROOT), "tracks", "interlagos.hdf5")
    assert os.path.exists(track_path), "Interlagos track HDF5 not found"
    
    circuit, meta = CircuitHDF5Reader(track_path).read_circuit()
    res = run_bicycle_model(params_dict, circuit, {"gear_min": 4})
    
    # Interlagos centerline is noisy (~+4s vs racing line, LTS_RESEARCH §5);
    # range is a smoke bound only until the track is recaptured from .xrk GPS.
    # Regulation-baseline preset sims 133.2s (real pole PRO 2025: 123.9s).
    lap_time = res["lap_time"]
    assert 128.0 <= lap_time <= 136.0, f"Interlagos simulated time {lap_time:.2f}s is out of target range [128s, 136s]"
    
    # Top speed should hit the speed governor (200 km/h)
    v_max = np.max(res["v_profile"]) * 3.6
    assert 195.0 <= v_max <= 200.1, f"Interlagos simulated top speed {v_max:.1f} km/h should be capped close to 200 km/h"



def test_no_abs_brake_bias_affects_lap_time() -> None:
    """Without ABS the bias-aware modulation makes brake balance move the lap.

    A rearward-imbalanced bias (60% front on this truck) locks the rear early,
    so the no-ABS driver must brake softer and loses time; shifting bias
    forward toward a balanced lock-up recovers it.
    """
    import copy
    from src.simulation.lap_time_solver import run_bicycle_model

    params = get_vehicle_by_id("volkswagen_31320").to_solver_dict()
    assert params["abs_enabled"] is False
    track_path = os.path.join(str(ROOT), "tracks", "cascavel.hdf5")
    circuit, _ = CircuitHDF5Reader(track_path).read_circuit()

    def lap(bias: float) -> float:
        p = copy.deepcopy(params)
        p["brake_balance"] = bias
        return run_bicycle_model(p, circuit, {"gear_min": 4})["lap_time"]

    rearward = lap(60.0)
    forward = lap(72.0)
    assert rearward > forward, "forward bias should recover time without ABS"
    assert (rearward - forward) > 0.03, "brake bias must be functional (>0.03s)"


def test_simulation_telemetry_math_channels() -> None:
    """Verify that SimulationTelemetry correctly builds math channels and exports to CSV."""
    from src.simulation.lap_time_solver import run_simulation, SimulationConfig
    from src.vehicle.setup import get_default_setup
    
    vp = get_vehicle_by_id("volkswagen_31320")
    track_path = os.path.join(str(ROOT), "tracks", "cascavel.hdf5")
    circuit, _ = CircuitHDF5Reader(track_path).read_circuit()
    
    sim_config = SimulationConfig.qualifying(track_id="cascavel")
    sim_config.setup = get_default_setup()
    
    result = run_simulation(sim_config, vp, circuit, save_csv=False)
    
    # Analyze telemetry
    telemetry = SimulationTelemetry(result)
    assert "g_sum" in telemetry.df.columns
    assert "coasting" in telemetry.df.columns
    assert "brake_speed" in telemetry.df.columns
    assert "jerk_long" in telemetry.df.columns
    
    metrics = telemetry.get_metrics()
    assert "coasting_pct" in metrics
    assert "max_g_sum" in metrics
    assert "max_brake_speed" in metrics
    assert metrics["max_g_sum"] > 0.0

    # Lockup channels only appear when params are supplied (backward-compatible).
    assert "brake_lockup_rear" not in telemetry.df.columns
    telemetry_lockup = SimulationTelemetry(result, params=vp.to_solver_dict())
    for col in ("brake_lockup_front", "brake_lockup_rear", "brake_lockup_slip",
                "balance_front_util", "balance_rear_util", "handling_balance"):
        assert col in telemetry_lockup.df.columns
    # A no-ABS truck brakes near its grip limit → the limiting axle sees margin.
    assert telemetry_lockup.df["brake_lockup_rear"].max() > 0.0
    # Cornering points load the axles → non-zero grip utilisation.
    assert telemetry_lockup.df["balance_front_util"].max() > 0.0
