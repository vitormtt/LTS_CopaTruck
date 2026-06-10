"""
Solver regression test suite.

Compares current simulation results for reference vehicles and tracks
against stored baselines in regression_baselines.json.

Run from project root:
    python3 -m pytest tests/test_solver_regression.py -v
"""
import os
import sys
import json
from pathlib import Path
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.vehicle.fleet import get_vehicle_by_id
from src.tracks.hdf5 import CircuitHDF5Reader
from src.simulation.lap_time_solver import run_simulation
from src.simulation.simulation_modes import SimulationConfig
from src.vehicle.setup import get_default_setup

# Path to the baseline file
BASELINE_PATH = ROOT / "tests" / "regression_baselines.json"


def load_baselines():
    """Load reference baselines from JSON file."""
    if not BASELINE_PATH.exists():
        pytest.fail(
            f"Baseline file not found at {BASELINE_PATH}. "
            "Run 'python3 tests/generate_regression_baselines.py' to generate it."
        )
    with open(BASELINE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# Parameterize the tests over the baseline cases
BASELINES = load_baselines()
CASE_IDS = list(BASELINES.keys())


def compute_array_stats(arr: np.ndarray) -> dict:
    """Compute summary statistics for an array to compare with baseline."""
    return {
        "length": int(len(arr)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr)),
    }


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_solver_regression(case_id: str) -> None:
    """Run simulation and compare results to stored baseline values."""
    baseline = BASELINES[case_id]
    vehicle_id = baseline["vehicle_id"]
    track_id = baseline["track_id"]
    mode = baseline["mode"]
    
    # Load vehicle
    vp = get_vehicle_by_id(vehicle_id)
    assert vp is not None, f"Vehicle {vehicle_id} not found"
    
    # Load track
    track_path = os.path.join(str(ROOT), "tracks", f"{track_id}.hdf5")
    assert os.path.exists(track_path), f"Track HDF5 not found at {track_path}"
    
    circuit, _ = CircuitHDF5Reader(track_path).read_circuit()
    
    # Configure simulation
    if mode == "qualifying":
        sim_config = SimulationConfig.qualifying(track_id=track_id)
    elif mode == "standing_start":
        sim_config = SimulationConfig.standing_start(track_id=track_id)
        if "porsche" not in vehicle_id:
            sim_config.launch_rpm = 1500.0  # Diesel truck launch RPM
    else:
        pytest.fail(f"Unknown mode: {mode}")
        
    sim_config.setup = get_default_setup(vehicle_id)
    
    # Run simulation
    result = run_simulation(sim_config, vp, circuit, save_csv=False)
    
    # 1. Convergence verification (finite values, no NaNs)
    assert np.all(np.isfinite(result.v_kmh)), "v_kmh contains NaN or Inf"
    assert np.all(np.isfinite(result.ax_long_g)), "ax_long_g contains NaN or Inf"
    assert np.all(np.isfinite(result.ay_lat_g)), "ay_lat_g contains NaN or Inf"
    assert np.all(np.isfinite(result.rpm)), "rpm contains NaN or Inf"
    assert np.all(np.isfinite(result.gear)), "gear contains NaN or Inf"
    assert np.all(np.isfinite(result.temp_tyre_c)), "temp_tyre_c contains NaN or Inf"
    
    # 2. Strict scalar convergence comparisons (tolerance = 1e-4)
    # lap_time should match baseline
    assert result.lap_time == pytest.approx(baseline["lap_time"], abs=1e-4), (
        f"Lap time regression in {case_id}: simulated={result.lap_time:.5f}s, baseline={baseline['lap_time']:.5f}s"
    )
    
    # Other metrics
    assert result.avg_speed_kmh == pytest.approx(baseline["avg_speed_kmh"], abs=1e-4)
    assert result.max_speed_kmh == pytest.approx(baseline["max_speed_kmh"], abs=1e-4)
    assert result.fuel_total_l == pytest.approx(baseline["fuel_total_l"], abs=1e-4)
    assert result.final_tyre_temp_c == pytest.approx(baseline["final_tyre_temp_c"], abs=1e-4)
    assert result.final_tyre_pressure_bar == pytest.approx(baseline["final_tyre_pressure_bar"], abs=1e-4)
    
    # 3. Channel array summary comparisons
    for channel_name, expected_stats in baseline["channels"].items():
        if channel_name == "v_kmh":
            actual_arr = result.v_kmh
        elif channel_name == "ax_long_g":
            actual_arr = result.ax_long_g
        elif channel_name == "ay_lat_g":
            actual_arr = result.ay_lat_g
        elif channel_name == "rpm":
            actual_arr = result.rpm
        elif channel_name == "gear":
            actual_arr = result.gear.astype(float)
        elif channel_name == "temp_tyre_c":
            actual_arr = result.temp_tyre_c
        else:
            continue
            
        actual_stats = compute_array_stats(actual_arr)
        
        assert actual_stats["length"] == expected_stats["length"], f"{channel_name} length mismatch"
        assert actual_stats["min"] == pytest.approx(expected_stats["min"], abs=1e-4)
        assert actual_stats["max"] == pytest.approx(expected_stats["max"], abs=1e-4)
        assert actual_stats["mean"] == pytest.approx(expected_stats["mean"], abs=1e-4)
        assert actual_stats["std"] == pytest.approx(expected_stats["std"], abs=1e-4)
