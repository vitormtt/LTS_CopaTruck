"""
Tests for the ENDURANCE_THERMAL mode (brake disc heat + fade).
"""
import sys
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.simulation.lap_time_solver import (  # noqa: E402
    _build_flat_params,
    _run_thermal_brake_model,
    run_simulation,
)
from src.simulation.simulation_modes import SimulationConfig  # noqa: E402
from src.tracks.hdf5 import CircuitHDF5Reader  # noqa: E402
from src.vehicle.fleet import get_vehicle_by_id  # noqa: E402
from src.vehicle.setup import get_default_setup  # noqa: E402


def _run(mode_cfg, vp):
    circuit, _ = CircuitHDF5Reader(
        str(ROOT / "tracks" / "cascavel.hdf5")
    ).read_circuit()
    mode_cfg.setup = get_default_setup("thermal_test")
    return run_simulation(mode_cfg, vp, circuit, save_csv=False)


@pytest.fixture(scope="module")
def thermal_result():
    vp = get_vehicle_by_id("volkswagen_31320")
    return _run(SimulationConfig.endurance_thermal(track_id="cascavel"), vp)


def test_disc_channels_present_only_in_thermal_mode(thermal_result) -> None:
    assert thermal_result.disc_temp_front_c is not None
    assert thermal_result.brake_fade_factor is not None

    quali = _run(SimulationConfig.qualifying(track_id="cascavel"),
                 get_vehicle_by_id("volkswagen_31320"))
    assert quali.disc_temp_front_c is None
    assert quali.peak_disc_temp_c is None
    assert "disc_temp_front_c" not in quali.to_dataframe().columns
    assert "disc_temp_front_c" in thermal_result.to_dataframe().columns


def test_disc_temperature_behaviour(thermal_result) -> None:
    """Disc heats in braking zones, cools on straights, stays bounded."""
    t_front = thermal_result.disc_temp_front_c
    assert np.max(t_front) > t_front[0] + 50.0, "disc never heated"
    assert np.any(np.diff(t_front) < 0.0), "disc never cooled"
    assert np.max(t_front) < 1000.0, "unphysical disc temperature"


def test_energy_balance() -> None:
    """Heat into discs must not exceed dissipated kinetic energy."""
    vp = get_vehicle_by_id("volkswagen_31320")
    p = _build_flat_params(vp)

    # Synthetic decel profile: 50 m/s down to 20 m/s over 100 steps
    n = 101
    v = np.linspace(50.0, 20.0, n)
    ds = np.full(n, 5.0)
    ds[0] = 0.0

    T_f, T_r, _ = _run_thermal_brake_model(v, ds, p, ambient_temp_c=25.0)

    m_total = p.m + p.initial_fuel_l * p.fuel_density
    e_kinetic = 0.5 * m_total * (v[0] ** 2 - v[-1] ** 2)
    heat_cap = p.disc_mass_kg * p.disc_specific_heat
    # Stored energy in 2 front + 2 rear discs (cooling only removes more)
    e_discs = 2.0 * heat_cap * ((T_f[-1] - T_f[0]) + (T_r[-1] - T_r[0]))

    assert e_discs <= e_kinetic + 1e-6, (
        f"disc energy {e_discs:.0f} J exceeds kinetic {e_kinetic:.0f} J"
    )
    assert e_discs > 0.0


def test_fade_disabled_equals_qualifying() -> None:
    """With fade unreachable the thermal lap is identical to qualifying."""
    vp = deepcopy(get_vehicle_by_id("volkswagen_31320"))
    vp.brake.fade_onset_temp_c = 1e6
    vp.brake.fade_full_temp_c = 2e6

    lap_thermal = _run(
        SimulationConfig.endurance_thermal(track_id="cascavel"), vp
    ).lap_time
    lap_quali = _run(
        SimulationConfig.qualifying(track_id="cascavel"), deepcopy(vp)
    ).lap_time

    assert lap_thermal == pytest.approx(lap_quali, abs=1e-9), (
        "thermal mode altered the solver result even without fade"
    )


def test_aggressive_fade_increases_lap_time(thermal_result) -> None:
    vp = deepcopy(get_vehicle_by_id("volkswagen_31320"))
    vp.brake.fade_onset_temp_c = 100.0
    vp.brake.fade_full_temp_c = 200.0
    lap_faded = _run(
        SimulationConfig.endurance_thermal(track_id="cascavel"), vp
    ).lap_time
    assert lap_faded > thermal_result.lap_time
    assert _run(
        SimulationConfig.endurance_thermal(track_id="cascavel"),
        get_vehicle_by_id("volkswagen_31320"),
    ).min_fade_factor == pytest.approx(1.0)  # default onset 450C not reached
