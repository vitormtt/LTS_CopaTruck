"""
Smoke tests for the OAT sensitivity analysis script.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.sensitivity_analysis import run_sensitivity  # noqa: E402


def test_sensitivity_two_params_structure() -> None:
    report = run_sensitivity(
        vehicle_id="volkswagen_31320",
        track_id="cascavel",
        pct=10.0,
        param_names=["mu", "mass"],
    )
    assert report["baseline_lap_time"] > 0
    rows = report["rows"]
    assert {r["name"] for r in rows} == {"mu", "mass"}
    by_name = {r["name"]: r for r in rows}
    # mu: more grip -> faster; mass: heavier -> slower
    assert by_name["mu"]["lap_plus"] < report["baseline_lap_time"]
    assert by_name["mass"]["lap_plus"] > report["baseline_lap_time"]
    # Rows sorted by descending |dLap|
    deltas = [r["delta_abs"] for r in rows]
    assert deltas == sorted(deltas, reverse=True)
