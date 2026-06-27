"""
Tests for the dynamic BSFC-based fuel consumption model.

Fuel is computed as BSFC x instantaneous delivered power x dt instead
of the legacy static L/km rate. The burned mass feeds back into the
vehicle dynamics (lighter car as the lap progresses).
"""
import sys
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.simulation.lap_time_solver import _fuel_step, run_simulation  # noqa: E402
from src.simulation.simulation_modes import SimulationConfig  # noqa: E402
from src.tracks.hdf5 import CircuitHDF5Reader  # noqa: E402
from saru_core.vehicle.engine import ICEEngine  # noqa: E402
from src.vehicle.fleet import get_vehicle_by_id  # noqa: E402
from src.vehicle.setup import get_default_setup  # noqa: E402


def _run_cascavel(vp):
    circuit, _ = CircuitHDF5Reader(
        str(ROOT / "tracks" / "cascavel.hdf5")
    ).read_circuit()
    config = SimulationConfig.qualifying(track_id="cascavel")
    config.setup = get_default_setup("fuel_test")
    return run_simulation(config, vp, circuit, save_csv=False)


@pytest.fixture(scope="module")
def vw_result():
    return _run_cascavel(get_vehicle_by_id("volkswagen_31320"))


def test_fuel_total_physical_window(vw_result) -> None:
    """Cascavel lap fuel must be physically plausible for a racing diesel."""
    assert 0.5 <= vw_result.fuel_total_l <= 3.0, (
        f"fuel_total_l={vw_result.fuel_total_l:.2f} outside [0.5, 3.0] L/lap"
    )
    # And clearly different from the legacy static rate (1.5 L/km x ~3 km)
    dist_km = vw_result.distance[-1] / 1000.0
    legacy_total = 1.5 * dist_km
    assert abs(vw_result.fuel_total_l - legacy_total) > 0.5


def test_fuel_monotonically_non_decreasing(vw_result) -> None:
    assert np.all(np.diff(vw_result.fuel_used_l) >= -1e-12)


def test_no_fuel_during_heavy_braking(vw_result) -> None:
    """Fuel increments must be ~zero where the car is decelerating hard."""
    v_ms = vw_result.v_kmh / 3.6
    dt = np.diff(vw_result.time)
    with np.errstate(divide="ignore", invalid="ignore"):
        a_actual = np.where(dt > 0, np.diff(v_ms) / dt, 0.0)
    fuel_inc = np.diff(vw_result.fuel_used_l)
    braking_steps = a_actual < -2.0  # heavy deceleration [m/s²]
    assert braking_steps.any(), "expected braking zones on Cascavel"
    assert np.all(fuel_inc[braking_steps] < 1e-6), (
        "fuel burned during overrun/braking should be zero"
    )


def test_heavier_fuel_load_slows_lap() -> None:
    """Doubling the initial fuel load must not make the lap faster."""
    vp_light = deepcopy(get_vehicle_by_id("volkswagen_31320"))
    vp_heavy = deepcopy(get_vehicle_by_id("volkswagen_31320"))
    vp_light.initial_fuel_l = 50.0
    vp_heavy.initial_fuel_l = 250.0
    lap_light = _run_cascavel(vp_light).lap_time
    lap_heavy = _run_cascavel(vp_heavy).lap_time
    assert lap_heavy > lap_light


def test_fuel_step_matches_ice_engine() -> None:
    """_fuel_step mirrors ICEEngine.get_fuel_consumption exactly."""
    bsfc, density = 210.0, 0.85
    engine = ICEEngine({"bsfc": bsfc, "fuel_density": density,
                        "max_power_kw": 850.0, "max_torque_nm": 4200.0,
                        "rpm_max": 3500.0, "rpm_idle": 800.0})
    for power_kw, dt in [(100.0, 0.05), (850.0, 0.5), (12.3, 1.7)]:
        expected = engine.get_fuel_consumption(power_kw, dt)
        assert _fuel_step(power_kw * 1000.0, dt, bsfc, density) == pytest.approx(
            expected, rel=1e-12
        )
