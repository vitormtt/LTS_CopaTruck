"""
Script to generate solver regression baselines.

Runs simulations for reference vehicles and tracks and saves their
KPIs and statistical summaries of telemetry channels to regression_baselines.json.

Run from project root:
    python3 tests/generate_regression_baselines.py
"""
import os
import sys
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.vehicle.fleet import get_vehicle_by_id
from src.tracks.hdf5 import CircuitHDF5Reader
from src.simulation.lap_time_solver import run_simulation
from src.simulation.simulation_modes import SimulationConfig
from src.vehicle.setup import get_default_setup


def compute_array_stats(arr: np.ndarray) -> dict:
    """Compute summary statistics for an array to save to baseline."""
    return {
        "length": int(len(arr)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr)),
    }


def main() -> None:
    print("Generating solver regression baselines...")
    
    cases = [
        {
            "id": "vw_31320_cascavel_qualifying",
            "vehicle_id": "volkswagen_31320",
            "track_id": "cascavel",
            "mode": "qualifying"
        },
        {
            "id": "vw_31320_cascavel_standing_start",
            "vehicle_id": "volkswagen_31320",
            "track_id": "cascavel",
            "mode": "standing_start"
        },
        {
            "id": "scania_r480_cascavel_qualifying",
            "vehicle_id": "scania_r480",
            "track_id": "cascavel",
            "mode": "qualifying"
        },
        {
            "id": "volvo_fh16_interlagos_qualifying",
            "vehicle_id": "volvo_fh16",
            "track_id": "interlagos",
            "mode": "qualifying"
        },

    ]
    
    baselines = {}
    
    for case in cases:
        case_id = case["id"]
        vehicle_id = case["vehicle_id"]
        track_id = case["track_id"]
        mode = case["mode"]
        
        print(f"Running simulation: {case_id}...")
        
        # Load vehicle
        vp = get_vehicle_by_id(vehicle_id)
        if vp is None:
            print(f"Error: vehicle {vehicle_id} not found", file=sys.stderr)
            sys.exit(1)
            
        # Load track
        track_path = os.path.join(str(ROOT), "tracks", f"{track_id}.hdf5")
        if not os.path.exists(track_path):
            print(f"Error: track {track_path} not found", file=sys.stderr)
            sys.exit(1)
            
        circuit, _ = CircuitHDF5Reader(track_path).read_circuit()
        
        # Configure simulation
        if mode == "qualifying":
            sim_config = SimulationConfig.qualifying(track_id=track_id)
        elif mode == "standing_start":
            sim_config = SimulationConfig.standing_start(track_id=track_id)
            if "porsche" not in vehicle_id:
                sim_config.launch_rpm = 1500.0  # Diesel truck launch RPM
        else:
            raise ValueError(f"Unknown mode: {mode}")
            
        sim_config.setup = get_default_setup(vehicle_id)
        
        # Run
        result = run_simulation(sim_config, vp, circuit, save_csv=False)
        
        # Package metrics
        baselines[case_id] = {
            "vehicle_id": vehicle_id,
            "track_id": track_id,
            "mode": mode,
            "lap_time": float(result.lap_time),
            "avg_speed_kmh": float(result.avg_speed_kmh),
            "max_speed_kmh": float(result.max_speed_kmh),
            "fuel_total_l": float(result.fuel_total_l),
            "final_tyre_temp_c": float(result.final_tyre_temp_c),
            "final_tyre_pressure_bar": float(result.final_tyre_pressure_bar),
            "channels": {
                "v_kmh": compute_array_stats(result.v_kmh),
                "ax_long_g": compute_array_stats(result.ax_long_g),
                "ay_lat_g": compute_array_stats(result.ay_lat_g),
                "rpm": compute_array_stats(result.rpm),
                "gear": compute_array_stats(result.gear.astype(float)),
                "temp_tyre_c": compute_array_stats(result.temp_tyre_c),
            }
        }
        
    output_path = ROOT / "tests" / "regression_baselines.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(baselines, f, indent=2)
        
    print(f"Successfully generated baselines at {output_path}")


if __name__ == "__main__":
    main()
