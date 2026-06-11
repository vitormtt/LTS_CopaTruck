"""
End-to-end simulation test — Porsche 911 GT3 Cup fleet.

Uses build_interlagos_real() (GPS-referenced, 4.309 km) instead of the
parametric approximation. Runs all 3 Porsche GT3 Cup profiles with two
setup configurations: default (wing 5, ARB 4/4) and high-downforce (wing 9).

Outputs:
    outputs/porsche_e2e/<vehicle_id>_<setup>.csv   — full telemetry channels
    KPI table printed in the terminal.

Run from project root:
    python run_porsche_e2e.py

Author: Lap Time Simulator Team
Date: 2026-03-10
"""

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from src.vehicle.fleet import get_vehicle_by_id
from src.vehicle.setup import VehicleSetup, apply_setup
from src.simulation.lap_time_solver import run_bicycle_model
from src.tracks.generate_br_tracks import build_interlagos_real

OUT_DIR = Path("outputs/porsche_e2e")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# SETUPS
# ---------------------------------------------------------------------------
SETUPS = {
    "default": VehicleSetup(
        arb_front=4, arb_rear=4, wing_position=5,
        tyre_pressure=1.8, brake_bias=-1.0,
        setup_name="default",
    ),
    "high_downforce": VehicleSetup(
        arb_front=5, arb_rear=3, wing_position=9,
        tyre_pressure=1.85, brake_bias=-0.5,
        setup_name="high_downforce",
    ),
}

VEHICLE_IDS = ["porsche_991_1", "porsche_991_2", "porsche_992_1"]

# GT3 Cup: gear_min=1 (full 6-gear range)
# Copa Truck callers: use gear_min=4
SOLVER_CONFIG = {"gear_min": 1}


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main() -> None:
    print("\n" + "=" * 64)
    print("  Porsche GT3 Cup — E2E Lap Time Simulation (Interlagos real)")
    print("=" * 64)

    circuit = build_interlagos_real(n_points=4000)

    header = (
        f"{'Vehicle':<35} {'Setup':<15} {'LapTime':>9}"
        f" {'Vmax':>8} {'Vmean':>8} {'T_tyre':>8} {'Fuel_L':>8}"
    )
    print(f"\n{header}")
    print("-" * len(header))

    for vid in VEHICLE_IDS:
        base_params = get_vehicle_by_id(vid)

        for setup_name, setup in SETUPS.items():
            params      = apply_setup(base_params, setup)
            solver_dict = params.to_solver_dict()
            solver_dict["k_roll"] = setup.arb_front_stiffness + setup.arb_rear_stiffness

            csv_path = OUT_DIR / f"{vid}_{setup_name}.csv"
            t0 = time.perf_counter()

            try:
                result  = run_bicycle_model(
                    params_dict=solver_dict,
                    circuit=circuit,
                    config=SOLVER_CONFIG,
                    save_csv=True,
                    out_path=str(csv_path),
                )
                elapsed = time.perf_counter() - t0

                lap_s  = result["lap_time"]
                v_kmh  = result["v_profile"] * 3.6
                vmax   = float(np.max(v_kmh))
                vmean  = float(np.mean(v_kmh))
                t_tyre = float(result["temp_pneu"][-1])
                fuel   = float(result["consumo"][-1])

                lap_str = f"{int(lap_s // 60)}:{lap_s % 60:06.3f}"
                print(
                    f"{params.name:<35} {setup_name:<15} {lap_str:>9}"
                    f" {vmax:>7.1f}k {vmean:>7.1f}k {t_tyre:>7.1f}C {fuel:>8.3f}L"
                )
                print(
                    f"  {'':35} {'':15}"
                    f" compute: {elapsed:.3f}s  -> {csv_path.name}"
                )

            except Exception as exc:
                import traceback
                print(
                    f"{params.name:<35} {setup_name:<15}"
                    f" [FAIL] {type(exc).__name__}: {exc}"
                )
                traceback.print_exc()

    print("\n" + "=" * 64)
    print(f"  Done. CSVs -> {OUT_DIR}/")
    print("=" * 64 + "\n")


if __name__ == "__main__":
    main()
