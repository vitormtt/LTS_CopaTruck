"""
Tests documenting the aero downforce coupling in the solver.

Downforce (negative Cl) increases F_normal in both solver passes,
raising cornering and braking limits — a downforce-equipped vehicle
must lap faster than the same vehicle without it.
"""
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.simulation.lap_time_solver import run_simulation  # noqa: E402
from src.simulation.simulation_modes import SimulationConfig  # noqa: E402
from src.tracks.hdf5 import CircuitHDF5Reader  # noqa: E402
from src.vehicle.fleet import get_vehicle_by_id  # noqa: E402
from src.vehicle.setup import get_default_setup  # noqa: E402


def _lap_time_with_cl(cl: float) -> float:
    vp = deepcopy(get_vehicle_by_id("volkswagen_31320"))
    vp.aero.lift_coefficient = cl
    circuit, _ = CircuitHDF5Reader(
        str(ROOT / "tracks" / "cascavel.hdf5")
    ).read_circuit()
    config = SimulationConfig.qualifying(track_id="cascavel")
    config.setup = get_default_setup("aero_test")
    result = run_simulation(config, vp, circuit, save_csv=False)
    return result.lap_time


def test_downforce_reduces_lap_time() -> None:
    """Cl = -3.0 (strong downforce) must lap faster than Cl = 0."""
    lap_no_df = _lap_time_with_cl(0.0)
    lap_with_df = _lap_time_with_cl(-3.0)
    assert lap_with_df < lap_no_df, (
        f"Downforce did not reduce lap time: {lap_with_df:.3f}s "
        f"vs {lap_no_df:.3f}s without"
    )
