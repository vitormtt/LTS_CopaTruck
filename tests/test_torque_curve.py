"""
Tests for the torque curve presets, validation and solver sensitivity.
"""
import json
import sys
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.simulation.lap_time_solver import (  # noqa: E402
    _torque_curve_interp,
    run_simulation,
)
from src.simulation.simulation_modes import SimulationConfig  # noqa: E402
from src.tracks.hdf5 import CircuitHDF5Reader  # noqa: E402
from src.vehicle.engine import ICEEngine  # noqa: E402  (import sanity)
from src.vehicle.fleet import get_vehicle_by_id  # noqa: E402
from src.vehicle.parameters import EngineParams  # noqa: E402
from src.vehicle.setup import get_default_setup  # noqa: E402

MODELS_PATH = ROOT / "data" / "vehicle_models.json"


def test_json_curves_match_synthetic_generation() -> None:
    """Preset JSON curves must be identical to the synthetic fallback.

    Guarantees that making the default curves explicit in
    data/vehicle_models.json changed no behavior (the regression suite
    passing untouched is the end-to-end proof; this is the unit-level
    counterpart).
    """
    with open(MODELS_PATH, encoding="utf-8") as f:
        models = json.load(f)

    for vid, m in models.items():
        assert "torque_curve_rpm" in m, f"{vid} missing explicit curve"
        synthetic = EngineParams(
            max_power=m["P_max"], max_torque=m["T_max"],
            rpm_max=m["rpm_max"], rpm_idle=m["rpm_idle"],
        )
        np.testing.assert_allclose(
            m["torque_curve_rpm"], synthetic.torque_curve_rpm, atol=1e-9,
            err_msg=f"{vid} RPM points differ from synthetic curve"
        )
        np.testing.assert_allclose(
            m["torque_curve_nm"], synthetic.torque_curve_nm, atol=1e-9,
            err_msg=f"{vid} torque points differ from synthetic curve"
        )


def test_engine_params_rejects_length_mismatch() -> None:
    with pytest.raises(ValueError, match="length"):
        EngineParams(
            max_power=850000.0, max_torque=4200.0,
            rpm_max=3500.0, rpm_idle=800.0,
            torque_curve_rpm=[800.0, 1300.0, 2100.0],
            torque_curve_nm=[1680.0, 4200.0],
        )


def test_engine_params_rejects_non_monotonic_rpm() -> None:
    with pytest.raises(ValueError, match="strictly increasing"):
        EngineParams(
            max_power=850000.0, max_torque=4200.0,
            rpm_max=3500.0, rpm_idle=800.0,
            torque_curve_rpm=[800.0, 2100.0, 1300.0],
            torque_curve_nm=[1680.0, 4200.0, 3990.0],
        )


def test_interp_rev_limiter_cuts_torque() -> None:
    """Above rpm_max the interpolated torque must be zero (fuel cut)."""
    rpm = [800.0, 1750.0, 2800.0, 3325.0, 3500.0]
    nm = [1680.0, 4200.0, 3990.0, 3360.0, 2520.0]
    assert _torque_curve_interp(3600.0, rpm, nm, rpm_max=3500.0) == 0.0
    assert _torque_curve_interp(1750.0, rpm, nm, rpm_max=3500.0) == pytest.approx(4200.0)


def test_raised_curve_reduces_lap_time() -> None:
    """Raising the whole torque curve by 10% must lap faster."""
    circuit, _ = CircuitHDF5Reader(
        str(ROOT / "tracks" / "cascavel.hdf5")
    ).read_circuit()

    def lap_with_scale(scale: float) -> float:
        vp = deepcopy(get_vehicle_by_id("volkswagen_31320"))
        vp.engine.torque_curve_nm = [t * scale for t in vp.engine.torque_curve_nm]
        config = SimulationConfig.qualifying(track_id="cascavel")
        config.setup = get_default_setup("torque_test")
        return run_simulation(config, vp, circuit, save_csv=False).lap_time

    assert lap_with_scale(1.10) < lap_with_scale(1.0)
