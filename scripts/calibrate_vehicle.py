"""
Vehicle parameter calibration from a reference speed trace.

Matches the simulated speed-vs-distance trace against a reference lap
(CSV with ``distance_m`` and ``v_kmh`` columns — the native format of
``SimulationResult.to_dataframe()`` and of
``src/tracks/telemetry_converter.py``). The objective is

    cost = RMSE(v_kmh on a common distance grid) + w * |delta lap_time|

minimised over the physical parameter vector
``[mu, Cx, Cl, torque_scale, max_decel, brake_balance]`` with a global
``scipy.optimize.differential_evolution`` stage followed by a local
``scipy.optimize.least_squares`` polish.

Outputs:
    - ``data/<vehicle>_calibrated.json`` — full flat preset (same schema
      as the entries of ``data/vehicle_models.json``, usable directly by
      ``VehicleParams.from_solver_dict``).
    - Markdown report with before/after metrics in ``src/results/``.

Usage:
    python3 scripts/calibrate_vehicle.py \
        --vehicle volkswagen_31320 --track interlagos \
        --reference src/results/lap_interlagos_ref.csv [--maxiter 20]

    # Optional: convert an AiM .xrk file first (requires libxrk):
    python3 scripts/calibrate_vehicle.py --vehicle volkswagen_31320 \
        --track interlagos --xrk "Perez-data/lap.xrk"

The 200 km/h speed governor is fixed by the Copa Truck regulations and
is intentionally NOT a calibration parameter.

Author: Lap Time Simulator Team
Date: 2026-06-11
"""

from __future__ import annotations

import argparse
import copy
import datetime
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.optimize import differential_evolution, least_squares

try:
    from .lts_common import (
        DATA_DIR,
        RESULTS_DIR,
        VehicleParams,
        load_circuit,
        load_vehicle,
        silence_solver_logging,
        simulate_lap,
    )
except ImportError:  # CLI execution from scripts/
    from lts_common import (
        DATA_DIR,
        RESULTS_DIR,
        VehicleParams,
        load_circuit,
        load_vehicle,
        silence_solver_logging,
        simulate_lap,
    )

# ---------------------------------------------------------------------------
# Calibration parameter space
# ---------------------------------------------------------------------------

#: Ordered names of the full calibration vector.
CALIBRATION_PARAMS: List[str] = [
    "mu", "Cx", "Cl", "torque_scale", "max_decel", "brake_balance",
]

#: Physical bounds per parameter (lower, upper).
PARAM_BOUNDS: Dict[str, Tuple[float, float]] = {
    "mu":            (1.00, 2.00),   # peak tyre friction [-]
    "Cx":            (0.50, 1.20),   # drag coefficient [-]
    "Cl":            (-0.50, 0.50),  # lift coefficient [-]
    "torque_scale":  (0.70, 1.30),   # torque-curve multiplier [-]
    "max_decel":     (6.00, 12.0),   # brake limit [m/s^2]
    "brake_balance": (50.0, 66.0),   # front brake bias [%]
}

#: Weight of |delta lap_time| [s] in the scalar cost (RMSE is in km/h).
LAP_TIME_WEIGHT: float = 2.0

#: Number of points of the common distance grid for resampling.
GRID_POINTS: int = 500


def get_param_vector(vp: VehicleParams) -> Dict[str, float]:
    """Extract the current calibration parameter values from a vehicle."""
    return {
        "mu": vp.tire.friction_coefficient,
        "Cx": vp.aero.drag_coefficient,
        "Cl": vp.aero.lift_coefficient,
        "torque_scale": 1.0,
        "max_decel": vp.brake.max_deceleration,
        "brake_balance": vp.brake.brake_balance,
    }


def apply_param_vector(
    base_vp: VehicleParams, values: Dict[str, float]
) -> VehicleParams:
    """Return a deep copy of ``base_vp`` with calibration values applied.

    Args:
        base_vp: Baseline vehicle (never mutated).
        values: Mapping of parameter name -> value; ``torque_scale`` is a
            multiplier applied to the baseline torque curve and peak
            torque, all other entries are absolute values.

    Returns:
        New VehicleParams instance.
    """
    vp = copy.deepcopy(base_vp)
    if "mu" in values:
        vp.tire.friction_coefficient = float(values["mu"])
    if "Cx" in values:
        vp.aero.drag_coefficient = float(values["Cx"])
    if "Cl" in values:
        vp.aero.lift_coefficient = float(values["Cl"])
    if "torque_scale" in values:
        scale = float(values["torque_scale"])
        vp.engine.torque_curve_nm = [
            t * scale for t in base_vp.engine.torque_curve_nm
        ]
        vp.engine.max_torque = base_vp.engine.max_torque * scale
    if "max_decel" in values:
        vp.brake.max_deceleration = float(values["max_decel"])
    if "brake_balance" in values:
        vp.brake.brake_balance = float(values["brake_balance"])
    return vp


# ---------------------------------------------------------------------------
# Reference handling
# ---------------------------------------------------------------------------

def load_reference_csv(path: str) -> pd.DataFrame:
    """Load a reference lap CSV requiring ``distance_m`` and ``v_kmh``.

    Args:
        path: CSV path (telemetry_converter or to_dataframe format).

    Returns:
        DataFrame sorted by distance with the two required columns.

    Raises:
        ValueError: If required columns are missing.
    """
    df = pd.read_csv(path)
    missing = {"distance_m", "v_kmh"} - set(df.columns)
    if missing:
        raise ValueError(
            f"Reference CSV '{path}' is missing columns {sorted(missing)}. "
            "Expected the to_dataframe()/telemetry_converter format with "
            "'distance_m' and 'v_kmh'."
        )
    df = df[["distance_m", "v_kmh"]].dropna().sort_values("distance_m")
    return df.reset_index(drop=True)


def resample_to_common_grid(
    sim_dist: np.ndarray,
    sim_v: np.ndarray,
    ref_dist: np.ndarray,
    ref_v: np.ndarray,
    n_points: int = GRID_POINTS,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Resample sim and reference speed traces onto a common distance grid.

    The grid spans the overlapping distance range of the two laps so a
    small lap-length mismatch (different track meshes) does not bias the
    error metric.

    Args:
        sim_dist: Simulated cumulative distance [m].
        sim_v: Simulated speed [km/h].
        ref_dist: Reference cumulative distance [m].
        ref_v: Reference speed [km/h].
        n_points: Grid resolution.

    Returns:
        Tuple ``(grid, v_sim_grid, v_ref_grid)``.
    """
    lo = max(float(sim_dist[0]), float(ref_dist[0]))
    hi = min(float(sim_dist[-1]), float(ref_dist[-1]))
    if hi <= lo:
        raise ValueError("Simulated and reference laps do not overlap in "
                         f"distance (sim {sim_dist[0]:.0f}-{sim_dist[-1]:.0f} m, "
                         f"ref {ref_dist[0]:.0f}-{ref_dist[-1]:.0f} m).")
    grid = np.linspace(lo, hi, n_points)
    v_sim = np.interp(grid, sim_dist, sim_v)
    v_ref = np.interp(grid, ref_dist, ref_v)
    return grid, v_sim, v_ref


def speed_rmse(v_sim: np.ndarray, v_ref: np.ndarray) -> float:
    """Root-mean-square speed error [km/h] on a common grid."""
    return float(np.sqrt(np.mean((v_sim - v_ref) ** 2)))


def estimate_reference_lap_time(ref: pd.DataFrame) -> float:
    """Estimate lap time [s] from the reference trace by integrating ds/v."""
    d = ref["distance_m"].to_numpy(dtype=float)
    v = np.maximum(ref["v_kmh"].to_numpy(dtype=float) / 3.6, 1.0)
    ds = np.diff(d)
    v_mid = 0.5 * (v[1:] + v[:-1])
    return float(np.sum(ds / v_mid))


# ---------------------------------------------------------------------------
# Calibration engine
# ---------------------------------------------------------------------------

@dataclass
class CalibrationResult:
    """Container for the calibration outcome.

    Attributes:
        vehicle_id: Calibrated fleet vehicle id.
        track_id: Track used for matching.
        free_params: Names of the optimised parameters (in order).
        initial_values: Parameter values before calibration.
        calibrated_values: Parameter values after calibration.
        initial_rmse_kmh: Speed RMSE before calibration [km/h].
        final_rmse_kmh: Speed RMSE after calibration [km/h].
        initial_lap_delta_s: |sim - ref| lap time before [s].
        final_lap_delta_s: |sim - ref| lap time after [s].
        initial_cost: Scalar objective before calibration.
        final_cost: Scalar objective after calibration.
        n_evaluations: Total number of solver evaluations.
        calibrated_params: Full calibrated VehicleParams.
    """

    vehicle_id: str
    track_id: str
    free_params: List[str]
    initial_values: Dict[str, float]
    calibrated_values: Dict[str, float]
    initial_rmse_kmh: float
    final_rmse_kmh: float
    initial_lap_delta_s: float
    final_lap_delta_s: float
    initial_cost: float
    final_cost: float
    n_evaluations: int = 0
    calibrated_params: Optional[VehicleParams] = field(
        default=None, repr=False)


class _Objective:
    """Callable objective evaluating one calibration vector.

    Wraps the solver call, resampling and metric computation, and counts
    evaluations. Failed solver runs return a large penalty so global
    optimisers can recover gracefully.
    """

    _PENALTY: float = 1.0e6

    def __init__(
        self,
        base_vp: VehicleParams,
        circuit: Any,
        track_id: str,
        ref: pd.DataFrame,
        free_params: List[str],
        lap_weight: float = LAP_TIME_WEIGHT,
    ) -> None:
        self.base_vp = base_vp
        self.circuit = circuit
        self.track_id = track_id
        self.ref_dist = ref["distance_m"].to_numpy(dtype=float)
        self.ref_v = ref["v_kmh"].to_numpy(dtype=float)
        self.ref_lap_time = estimate_reference_lap_time(ref)
        self.free_params = free_params
        self.lap_weight = lap_weight
        self.n_evaluations = 0

    def metrics(self, x: np.ndarray) -> Tuple[float, float, np.ndarray]:
        """Return ``(rmse_kmh, lap_delta_s, speed_residuals)`` for ``x``."""
        self.n_evaluations += 1
        values = dict(zip(self.free_params, [float(v) for v in x]))
        vp = apply_param_vector(self.base_vp, values)
        try:
            result = simulate_lap(vp, self.circuit, self.track_id)
        except Exception:
            n = GRID_POINTS
            return self._PENALTY, self._PENALTY, np.full(n, self._PENALTY)
        _, v_sim, v_ref = resample_to_common_grid(
            result.distance, result.v_kmh, self.ref_dist, self.ref_v)
        rmse = speed_rmse(v_sim, v_ref)
        lap_delta = abs(result.lap_time - self.ref_lap_time)
        return rmse, lap_delta, v_sim - v_ref

    def cost(self, x: np.ndarray) -> float:
        """Scalar objective: RMSE [km/h] + weight * |delta lap| [s]."""
        rmse, lap_delta, _ = self.metrics(x)
        return rmse + self.lap_weight * lap_delta

    def residuals(self, x: np.ndarray) -> np.ndarray:
        """Residual vector for least_squares (speed errors + lap term)."""
        rmse, lap_delta, res = self.metrics(x)
        n = len(res)
        # Scale so that sum(res^2)/n ~ RMSE^2 and append the weighted lap
        # term so least_squares minimises the same composite objective.
        lap_term = np.sqrt(self.lap_weight * lap_delta * max(n, 1))
        _ = rmse  # rmse implied by res; kept for clarity
        return np.concatenate([res / np.sqrt(n), [lap_term / np.sqrt(n)]])


def calibrate(
    vehicle_id: str,
    track_id: str,
    reference: pd.DataFrame,
    free_params: Optional[List[str]] = None,
    use_de: bool = True,
    maxiter: int = 20,
    popsize: int = 10,
    lap_weight: float = LAP_TIME_WEIGHT,
    seed: int = 42,
    max_nfev_polish: int = 60,
) -> CalibrationResult:
    """Calibrate vehicle parameters against a reference speed trace.

    Args:
        vehicle_id: Fleet registry vehicle key (baseline preset).
        track_id: Track id matching the reference lap.
        reference: DataFrame with ``distance_m`` and ``v_kmh``.
        free_params: Subset of :data:`CALIBRATION_PARAMS` to optimise
            (default: all six).
        use_de: Run the global differential-evolution stage before the
            local least-squares polish.
        maxiter: DE generations.
        popsize: DE population multiplier.
        lap_weight: Weight of |delta lap_time| in the scalar cost.
        seed: RNG seed for reproducibility.
        max_nfev_polish: Function-evaluation budget of the LS polish.

    Returns:
        CalibrationResult with before/after metrics and the calibrated
        VehicleParams.
    """
    free_params = list(free_params or CALIBRATION_PARAMS)
    unknown = set(free_params) - set(CALIBRATION_PARAMS)
    if unknown:
        raise ValueError(f"Unknown calibration parameters: {sorted(unknown)}."
                         f" Available: {CALIBRATION_PARAMS}")

    circuit = load_circuit(track_id)
    base_vp = load_vehicle(vehicle_id)
    objective = _Objective(base_vp, circuit, track_id, reference,
                           free_params, lap_weight)

    initial_all = get_param_vector(base_vp)
    x0 = np.array([initial_all[p] for p in free_params], dtype=float)
    bounds = [PARAM_BOUNDS[p] for p in free_params]
    x0 = np.clip(x0, [b[0] for b in bounds], [b[1] for b in bounds])

    rmse0, lap_delta0, _ = objective.metrics(x0)
    cost0 = rmse0 + lap_weight * lap_delta0

    best_x = x0.copy()
    if use_de:
        de_result = differential_evolution(
            objective.cost,
            bounds=bounds,
            maxiter=maxiter,
            popsize=popsize,
            seed=seed,
            tol=1e-3,
            polish=False,
            init="sobol",
            updating="deferred",
        )
        if np.isfinite(de_result.fun):
            best_x = np.asarray(de_result.x, dtype=float)

    lower = np.array([b[0] for b in bounds])
    upper = np.array([b[1] for b in bounds])
    ls_result = least_squares(
        objective.residuals,
        x0=np.clip(best_x, lower, upper),
        bounds=(lower, upper),
        diff_step=0.02,
        max_nfev=max_nfev_polish,
    )
    candidate = np.asarray(ls_result.x, dtype=float)

    # Keep whichever point is best under the composite scalar cost.
    if objective.cost(candidate) <= objective.cost(best_x):
        best_x = candidate

    rmse1, lap_delta1, _ = objective.metrics(best_x)
    cost1 = rmse1 + lap_weight * lap_delta1

    calibrated_values = dict(zip(free_params, [float(v) for v in best_x]))
    calibrated_vp = apply_param_vector(base_vp, calibrated_values)

    return CalibrationResult(
        vehicle_id=vehicle_id,
        track_id=track_id,
        free_params=free_params,
        initial_values={p: float(initial_all[p]) for p in free_params},
        calibrated_values=calibrated_values,
        initial_rmse_kmh=rmse0,
        final_rmse_kmh=rmse1,
        initial_lap_delta_s=lap_delta0,
        final_lap_delta_s=lap_delta1,
        initial_cost=cost0,
        final_cost=cost1,
        n_evaluations=objective.n_evaluations,
        calibrated_params=calibrated_vp,
    )


# ---------------------------------------------------------------------------
# Persistence — calibrated preset + Markdown report
# ---------------------------------------------------------------------------

def save_calibrated_preset(result: CalibrationResult) -> str:
    """Write ``data/<vehicle>_calibrated.json`` as a full flat preset.

    Reads the existing flat preset from ``data/vehicle_models.json`` as a
    template (preserving every field, including metadata) and overwrites
    only the calibrated entries. The output is directly loadable with
    ``VehicleParams.from_solver_dict``.

    Args:
        result: Calibration outcome.

    Returns:
        Path of the written JSON file.
    """
    models_path = DATA_DIR / "vehicle_models.json"
    with open(models_path, "r", encoding="utf-8") as f:
        models = json.load(f)
    if result.vehicle_id not in models:
        raise KeyError(
            f"Vehicle '{result.vehicle_id}' not found in {models_path} "
            f"(available: {list(models)})")

    preset: Dict[str, Any] = dict(models[result.vehicle_id])
    values = result.calibrated_values
    if "mu" in values:
        preset["mu"] = round(values["mu"], 4)
    if "Cx" in values:
        preset["Cx"] = round(values["Cx"], 4)
    if "Cl" in values:
        preset["Cl"] = round(values["Cl"], 4)
    if "torque_scale" in values:
        scale = values["torque_scale"]
        preset["torque_curve_nm"] = [
            round(t * scale, 1) for t in preset["torque_curve_nm"]
        ]
        preset["T_max"] = round(preset["T_max"] * scale, 1)
    if "max_decel" in values:
        preset["max_decel"] = round(values["max_decel"], 3)
    if "brake_balance" in values:
        preset["brake_balance"] = round(values["brake_balance"], 2)
    preset["name"] = f"{preset.get('name', result.vehicle_id)} [calibrated]"
    preset["calibration"] = {
        "date": datetime.datetime.now().isoformat(timespec="seconds"),
        "track_id": result.track_id,
        "free_params": result.free_params,
        "rmse_kmh_before": round(result.initial_rmse_kmh, 3),
        "rmse_kmh_after": round(result.final_rmse_kmh, 3),
        "lap_delta_s_before": round(result.initial_lap_delta_s, 3),
        "lap_delta_s_after": round(result.final_lap_delta_s, 3),
    }

    out_path = DATA_DIR / f"{result.vehicle_id}_calibrated.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(preset, f, indent=2, ensure_ascii=False)
    return str(out_path)


def save_markdown_report(result: CalibrationResult,
                         reference_path: str) -> str:
    """Write the before/after calibration report to ``src/results/``."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = RESULTS_DIR / (
        f"calibration_{result.vehicle_id}_{result.track_id}_{stamp}.md")

    lines = [
        f"# Calibration Report — {result.vehicle_id} @ {result.track_id}",
        "",
        f"- Date: {datetime.datetime.now().isoformat(timespec='seconds')}",
        f"- Reference: `{reference_path}`",
        f"- Free parameters: {', '.join(result.free_params)}",
        f"- Solver evaluations: {result.n_evaluations}",
        "",
        "## Metrics",
        "",
        "| Metric | Before | After |",
        "|---|---:|---:|",
        f"| Speed RMSE [km/h] | {result.initial_rmse_kmh:.3f} "
        f"| {result.final_rmse_kmh:.3f} |",
        f"| &#124;Δ lap time&#124; [s] | {result.initial_lap_delta_s:.3f} "
        f"| {result.final_lap_delta_s:.3f} |",
        f"| Composite cost | {result.initial_cost:.3f} "
        f"| {result.final_cost:.3f} |",
        "",
        "## Parameters",
        "",
        "| Parameter | Initial | Calibrated |",
        "|---|---:|---:|",
    ]
    for p in result.free_params:
        lines.append(f"| {p} | {result.initial_values[p]:.4f} "
                     f"| {result.calibrated_values[p]:.4f} |")
    lines += [
        "",
        "Objective: `RMSE(v_kmh) + w·|Δlap_time|` on a common distance "
        f"grid ({GRID_POINTS} points), w = {LAP_TIME_WEIGHT}. Global stage: "
        "scipy differential_evolution; local polish: least_squares "
        "(bounded, 2-point finite differences).",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


# ---------------------------------------------------------------------------
# Optional .xrk conversion (degrades gracefully without libxrk)
# ---------------------------------------------------------------------------

def maybe_convert_xrk(xrk_path: str, csv_out: Optional[str] = None) -> str:
    """Convert an AiM .xrk file to CSV if ``libxrk`` is installed.

    Args:
        xrk_path: Path to the .xrk telemetry file.
        csv_out: Output CSV path (default: alongside the .xrk).

    Returns:
        Path of the produced CSV.

    Raises:
        SystemExit: With a clear installation hint when libxrk is absent.
    """
    try:
        import libxrk  # noqa: F401
    except ImportError:
        raise SystemExit(
            "ERROR: converting .xrk telemetry requires the 'libxrk' "
            "package, which is not installed in this environment.\n"
            "Install it locally with:\n"
            "    pip install libxrk\n"
            "then re-run this command, or pre-convert the lap with\n"
            "    python3 -c \"from src.tracks.telemetry_converter import "
            "convert_xrk_to_csv; convert_xrk_to_csv('<file>.xrk', "
            "'<out>.csv')\"\n"
            "and pass the CSV via --reference instead."
        )
    from src.tracks.telemetry_converter import convert_xrk_to_csv
    out = csv_out or str(Path(xrk_path).with_suffix(".csv"))
    convert_xrk_to_csv(xrk_path, out)
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Calibrate vehicle parameters against a reference "
                    "speed trace (speed-trace matching).")
    parser.add_argument("--vehicle", required=True,
                        help="Fleet vehicle id (e.g. volkswagen_31320)")
    parser.add_argument("--track", required=True,
                        help="Track id in tracks/*.hdf5 (e.g. interlagos)")
    parser.add_argument("--reference", default=None,
                        help="Reference lap CSV with distance_m and v_kmh")
    parser.add_argument("--xrk", default=None,
                        help="AiM .xrk file to convert first (needs libxrk)")
    parser.add_argument("--maxiter", type=int, default=20,
                        help="Differential evolution generations (default 20)")
    parser.add_argument("--popsize", type=int, default=10,
                        help="DE population multiplier (default 10)")
    parser.add_argument("--no-de", action="store_true",
                        help="Skip the global DE stage (least-squares only)")
    parser.add_argument("--params", nargs="*", default=None,
                        help=f"Subset of {CALIBRATION_PARAMS} to optimise")
    args = parser.parse_args(argv)

    silence_solver_logging()

    reference_path = args.reference
    if args.xrk is not None:
        reference_path = maybe_convert_xrk(args.xrk)
        print(f"Converted {args.xrk} -> {reference_path}")
    if reference_path is None:
        parser.error("provide --reference <csv> or --xrk <file>")

    reference = load_reference_csv(reference_path)
    print(f"Reference: {reference_path} "
          f"({len(reference)} samples, "
          f"{reference['distance_m'].iloc[-1]:.0f} m, "
          f"~{estimate_reference_lap_time(reference):.2f} s)")

    result = calibrate(
        vehicle_id=args.vehicle,
        track_id=args.track,
        reference=reference,
        free_params=args.params,
        use_de=not args.no_de,
        maxiter=args.maxiter,
        popsize=args.popsize,
    )

    print(f"\nCalibration finished ({result.n_evaluations} solver runs)")
    print(f"  Speed RMSE : {result.initial_rmse_kmh:8.3f} -> "
          f"{result.final_rmse_kmh:8.3f} km/h")
    print(f"  |dLap|     : {result.initial_lap_delta_s:8.3f} -> "
          f"{result.final_lap_delta_s:8.3f} s")
    print(f"  Cost       : {result.initial_cost:8.3f} -> "
          f"{result.final_cost:8.3f}")
    for p in result.free_params:
        print(f"  {p:<14}: {result.initial_values[p]:10.4f} -> "
              f"{result.calibrated_values[p]:10.4f}")

    preset_path = save_calibrated_preset(result)
    report_path = save_markdown_report(result, reference_path)
    print(f"\nCalibrated preset: {preset_path}")
    print(f"Report           : {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
