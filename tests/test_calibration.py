"""
Synthetic round-trip test for the telemetry calibration pipeline.

Generates a "real" reference by simulating a perturbed vehicle, then
checks that scripts/calibrate_vehicle.py recovers the perturbation
direction and reduces the speed-trace error. Uses the least_squares
stage only (no differential evolution) to stay fast in CI.
"""
import sys
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.calibrate_vehicle import calibrate, load_reference_csv  # noqa: E402
from scripts.lts_common import load_circuit, simulate_lap  # noqa: E402
from src.vehicle.fleet import get_vehicle_by_id  # noqa: E402

TRUE_MU_SCALE = 0.95
TRUE_TORQUE_SCALE = 1.05


@pytest.fixture(scope="module")
def synthetic_reference(tmp_path_factory):
    """Simulate a perturbed vehicle and export its speed trace."""
    circuit = load_circuit("cascavel")
    vp = deepcopy(get_vehicle_by_id("volkswagen_31320"))
    vp.tire.friction_coefficient *= TRUE_MU_SCALE
    vp.engine.torque_curve_nm = [
        t * TRUE_TORQUE_SCALE for t in vp.engine.torque_curve_nm
    ]
    result = simulate_lap(vp, circuit, "cascavel")
    path = tmp_path_factory.mktemp("calib") / "reference.csv"
    result.to_dataframe()[["distance_m", "v_kmh"]].to_csv(path, index=False)
    return str(path), result.lap_time


def test_calibration_round_trip(synthetic_reference) -> None:
    ref_path, true_lap = synthetic_reference
    ref = load_reference_csv(ref_path)

    outcome = calibrate(
        vehicle_id="volkswagen_31320",
        track_id="cascavel",
        reference=ref,
        free_params=["mu", "torque_scale"],
        use_de=False,
    )

    assert outcome.final_rmse_kmh < outcome.initial_rmse_kmh * 0.5, (
        f"calibration did not reduce error: "
        f"{outcome.initial_rmse_kmh:.3f} -> {outcome.final_rmse_kmh:.3f} km/h"
    )
    assert outcome.final_lap_delta_s < 0.2  # [s]

    base_mu = get_vehicle_by_id("volkswagen_31320").tire.friction_coefficient
    mu_cal = outcome.calibrated_values["mu"]
    torque_cal = outcome.calibrated_values["torque_scale"]
    # Recovered values move in the perturbation direction
    assert mu_cal < base_mu
    assert torque_cal > 1.0
    # And land near the true values
    assert mu_cal == pytest.approx(base_mu * TRUE_MU_SCALE, rel=0.03)
    assert torque_cal == pytest.approx(TRUE_TORQUE_SCALE, rel=0.03)
