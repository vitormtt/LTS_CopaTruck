"""
Live-parameter tests: every UI-exposed parameter must affect the physics.

The 2026-06 audit found several parameters exposed in the UI with ZERO
effect on the solver (delta lap = 0.0000 s). Physics v2 made them live;
this suite pins that property so they can never silently die again.
"""
import sys
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.simulation.lap_time_solver import run_simulation  # noqa: E402
from src.simulation.simulation_modes import SimulationConfig  # noqa: E402
from src.tracks.hdf5 import CircuitHDF5Reader  # noqa: E402
from src.vehicle.fleet import get_vehicle_by_id  # noqa: E402
from src.vehicle.setup import get_default_setup  # noqa: E402

_CIRCUIT = CircuitHDF5Reader(str(ROOT / "tracks" / "cascavel.hdf5")).read_circuit()[0]


def _run(mutate=None):
    vp = deepcopy(get_vehicle_by_id("volkswagen_31320"))
    if mutate is not None:
        mutate(vp)
    cfg = SimulationConfig.qualifying(track_id="cascavel")
    cfg.setup = get_default_setup("live_params")
    return run_simulation(cfg, vp, _CIRCUIT, save_csv=False)


@pytest.fixture(scope="module")
def ref():
    return _run()


def test_max_power_caps_traction(ref) -> None:
    """B1 fix: halving P_max must slow the lap (torque curve clamped)."""
    r = _run(lambda v: setattr(v.engine, "max_power", v.engine.max_power / 2))
    assert r.lap_time > ref.lap_time + 0.5


def test_cl_sign_is_physical(ref) -> None:
    """B2 fix: lift (Cl>0) slows, downforce (Cl<0) speeds up."""
    lift = _run(lambda v: setattr(v.aero, "lift_coefficient", 1.0))
    df = _run(lambda v: setattr(v.aero, "lift_coefficient", -1.0))
    assert lift.lap_time > ref.lap_time
    assert df.lap_time < ref.lap_time


def test_brake_telemetry_consistent(ref) -> None:
    """B4 fix: brake channel reflects the final speed profile."""
    v_ms = ref.v_kmh / 3.6
    dt = np.diff(ref.time)
    with np.errstate(divide="ignore", invalid="ignore"):
        a_real = np.where(dt > 0, np.diff(v_ms) / dt, 0.0)
    heavy = a_real < -2.0
    assert heavy.any()
    # Peak decel in the channel must match the profile-derived decel
    assert ref.peak_brake_g < -0.7
    overlap = (ref.brake_pct[:-1] > 5.0)[heavy].mean()
    assert overlap > 0.9, f"brake channel covers only {overlap:.0%} of braking"


def test_driveline_efficiency_live(ref) -> None:
    r = _run(lambda v: setattr(v.transmission, "transmission_efficiency", 0.80))
    assert r.lap_time > ref.lap_time


def test_shift_time_live(ref) -> None:
    r = _run(lambda v: setattr(v.transmission, "shift_time", 0.6))
    assert r.lap_time > ref.lap_time


def test_pacejka_d_live(ref) -> None:
    r = _run(lambda v: setattr(v.tire, "pacejka_D", 0.9))
    assert r.lap_time > ref.lap_time


def test_pacejka_bc_shape_slip_channels(ref) -> None:
    """B/C set the slip angle at the Magic-Formula peak (channel-level).

    A stiffer tyre (higher B) peaks at a smaller slip angle, so the
    saturation cap clips the slip channels earlier.
    """
    r = _run(lambda v: setattr(v.tire, "pacejka_B", 20.0))
    assert not np.allclose(r.front_slip_angle_deg, ref.front_slip_angle_deg)
    assert np.max(r.front_slip_angle_deg) < np.max(ref.front_slip_angle_deg)


def test_cornering_stiffness_live_in_channels(ref) -> None:
    """Cf/Cr drive slip angles and steady-state steering."""
    def softer(v):
        v.tire.cornering_stiffness_front = 70000.0
    r = _run(softer)
    assert np.max(r.front_slip_angle_deg) > np.max(ref.front_slip_angle_deg)
    assert not np.allclose(r.steering_deg, ref.steering_deg)
    assert r.understeer_margin_deg > ref.understeer_margin_deg


def test_iz_live(ref) -> None:
    """Quasi-transient yaw cap: huge Iz must cost lap time."""
    r = _run(lambda v: setattr(v.mass_geometry, "Iz", 300000.0))
    assert r.lap_time > ref.lap_time


def test_brake_response_time_live(ref) -> None:
    r = _run(lambda v: setattr(v.brake, "brake_response_time", 0.8))
    assert r.lap_time > ref.lap_time


def test_abs_live(ref) -> None:
    """Disabling ABS applies the driver-modulation margin."""
    r = _run(lambda v: setattr(v.brake, "abs_enabled", False))
    assert r.lap_time > ref.lap_time


def test_weight_distribution_live(ref) -> None:
    def front_heavy(v):
        wb = v.mass_geometry.wheelbase
        v.mass_geometry.lf = wb * 0.40   # rear share 40%
        v.mass_geometry.lr = wb * 0.60
    r = _run(front_heavy)
    assert r.lap_time != pytest.approx(ref.lap_time, abs=1e-6)


def test_track_width_live(ref) -> None:
    def narrow(v):
        v.mass_geometry.track_width_front = 1.8
        v.mass_geometry.track_width_rear = 1.8
    r = _run(narrow)
    assert r.lap_time > ref.lap_time  # more load transfer, less grip


def test_standing_start_slower_than_qualifying() -> None:
    """Physical sanity restored by the unified passes."""
    vp = get_vehicle_by_id("volkswagen_31320")
    cfg_q = SimulationConfig.qualifying(track_id="cascavel")
    cfg_q.setup = get_default_setup("q")
    cfg_s = SimulationConfig.standing_start(track_id="cascavel")
    cfg_s.setup = get_default_setup("s")
    cfg_s.launch_rpm = 1500.0
    lap_q = run_simulation(cfg_q, vp, _CIRCUIT, save_csv=False).lap_time
    lap_s = run_simulation(cfg_s, deepcopy(vp), _CIRCUIT, save_csv=False).lap_time
    assert lap_s > lap_q
