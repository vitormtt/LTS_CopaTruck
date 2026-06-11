"""
One-at-a-time (OAT) sensitivity analysis for the lap time simulator.

Perturbs each physical vehicle parameter by +/- pct% around its baseline
value, re-runs the qualifying lap and ranks the parameters by absolute
lap-time swing (tornado table). Results are printed to stdout and saved
as a Markdown report + CSV in ``src/results/``.

Usage:
    python3 scripts/sensitivity_analysis.py \
        --vehicle volkswagen_31320 --track cascavel --pct 10

Notes:
    - The 200 km/h speed governor is mandated by the Copa Truck
      regulations and is therefore *not* a calibration/sensitivity
      parameter.
    - ``apply_setup`` overwrites roll stiffness from the discrete ARB
      lookup, so the roll-stiffness split is perturbed through
      ``ContinuousArbSetup`` (see ``lts_common``).

Author: Lap Time Simulator Team
Date: 2026-06-11
"""

from __future__ import annotations

import argparse
import copy
import datetime
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd

try:
    from .lts_common import (
        RESULTS_DIR,
        ContinuousArbSetup,
        VehicleParams,
        load_circuit,
        load_vehicle,
        silence_solver_logging,
        simulate_lap,
    )
except ImportError:  # CLI execution from scripts/
    from lts_common import (
        RESULTS_DIR,
        ContinuousArbSetup,
        VehicleParams,
        load_circuit,
        load_vehicle,
        silence_solver_logging,
        simulate_lap,
    )
from src.vehicle.setup import (
    _TYRE_PRESSURE_MAX,
    _TYRE_PRESSURE_MIN,
    get_default_setup,
)

# Setter signature: (vehicle_params, baseline_value, scale_factor) -> None
_Setter = Callable[[VehicleParams, float, float], None]


@dataclass
class ParamSpec:
    """Specification of one perturbable physical parameter.

    Attributes:
        name: Short identifier used in tables and the CLI.
        description: Human-readable description with units.
        baseline: Callable extracting the baseline value from the vehicle.
        setter: Callable applying ``baseline * scale`` to a params copy.
    """

    name: str
    description: str
    baseline: Callable[[VehicleParams], float]
    setter: _Setter


def _scale_torque(vp: VehicleParams, _base: float, scale: float) -> None:
    """Scale the full torque curve (and peak torque) multiplicatively."""
    vp.engine.torque_curve_nm = [t * scale for t in vp.engine.torque_curve_nm]
    vp.engine.max_torque *= scale


def _scale_track_widths(vp: VehicleParams, _base: float, scale: float) -> None:
    """Scale front and rear track widths together."""
    vp.mass_geometry.track_width_front *= scale
    vp.mass_geometry.track_width_rear *= scale


def _default_front_roll_share() -> float:
    """Front fraction of total roll stiffness in the default setup [-]."""
    default = get_default_setup()
    k_total = default.arb_front_stiffness + default.arb_rear_stiffness
    return float(default.arb_front_stiffness / k_total)


def _build_param_specs() -> List[ParamSpec]:
    """Return the list of physical parameters for the OAT sweep."""

    def set_attr(path: str) -> _Setter:
        obj_name, attr = path.split(".")

        def _setter(vp: VehicleParams, base: float, scale: float) -> None:
            setattr(getattr(vp, obj_name), attr, base * scale)

        return _setter

    def get_attr(path: str) -> Callable[[VehicleParams], float]:
        obj_name, attr = path.split(".")
        return lambda vp: float(getattr(getattr(vp, obj_name), attr))

    return [
        ParamSpec("mu", "Tyre friction coefficient [-]",
                  get_attr("tire.friction_coefficient"),
                  set_attr("tire.friction_coefficient")),
        ParamSpec("Cd", "Aerodynamic drag coefficient Cx [-]",
                  get_attr("aero.drag_coefficient"),
                  set_attr("aero.drag_coefficient")),
        ParamSpec("Cl", "Aerodynamic lift coefficient [-]",
                  get_attr("aero.lift_coefficient"),
                  set_attr("aero.lift_coefficient")),
        ParamSpec("A_front", "Frontal area [m^2]",
                  get_attr("aero.frontal_area"),
                  set_attr("aero.frontal_area")),
        ParamSpec("mass", "Total vehicle mass [kg]",
                  get_attr("mass_geometry.mass"),
                  set_attr("mass_geometry.mass")),
        ParamSpec("h_cg", "Centre-of-gravity height [m]",
                  get_attr("mass_geometry.cg_height"),
                  set_attr("mass_geometry.cg_height")),
        ParamSpec("track_width", "Front+rear track width [m]",
                  lambda vp: float(vp.mass_geometry.track_width_avg),
                  _scale_track_widths),
        ParamSpec("k_roll_front_share", "Front share of total roll stiffness [-]",
                  lambda vp: _default_front_roll_share(),
                  lambda vp, b, s: None),  # handled via setup, see run
        ParamSpec("torque_scale", "Engine torque curve scale [-]",
                  lambda vp: 1.0, _scale_torque),
        ParamSpec("max_decel", "Brake max deceleration [m/s^2]",
                  get_attr("brake.max_deceleration"),
                  set_attr("brake.max_deceleration")),
        ParamSpec("brake_balance", "Front brake balance [%]",
                  get_attr("brake.brake_balance"),
                  set_attr("brake.brake_balance")),
        ParamSpec("final_drive", "Final drive ratio [-]",
                  get_attr("transmission.final_drive_ratio"),
                  set_attr("transmission.final_drive_ratio")),
        ParamSpec("tyre_pressure", "Cold tyre pressure [bar]",
                  lambda vp: float(get_default_setup().tyre_pressure),
                  lambda vp, b, s: None),  # handled via setup, see run
    ]


PARAM_NAMES: List[str] = [spec.name for spec in _build_param_specs()]


def _lap_with_setup_param(
    base_vp: VehicleParams,
    circuit: Any,
    track_id: str,
    param: str,
    scale: float,
) -> float:
    """Run a lap perturbing a setup-level parameter (pressure / roll split)."""
    default = get_default_setup()
    setup = ContinuousArbSetup()
    if param == "tyre_pressure":
        setup.tyre_pressure = float(
            np.clip(default.tyre_pressure * scale,
                    _TYRE_PRESSURE_MIN, _TYRE_PRESSURE_MAX)
        )
    elif param == "k_roll_front_share":
        k_total = default.arb_front_stiffness + default.arb_rear_stiffness
        share = default.arb_front_stiffness / k_total
        new_share = float(np.clip(share * scale, 0.05, 0.95))
        setup.k_front_override = k_total * new_share
        setup.k_rear_override = k_total * (1.0 - new_share)
    else:  # pragma: no cover — guarded by caller
        raise ValueError(f"Unknown setup-level parameter: {param}")
    return simulate_lap(base_vp, circuit, track_id, setup=setup).lap_time


_SETUP_LEVEL_PARAMS = ("tyre_pressure", "k_roll_front_share")


def run_sensitivity(
    vehicle_id: str = "volkswagen_31320",
    track_id: str = "cascavel",
    pct: float = 10.0,
    param_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Run the OAT +/- pct% sensitivity sweep.

    Args:
        vehicle_id: Fleet registry vehicle key.
        track_id: Track file stem in ``tracks/``.
        pct: Perturbation amplitude in percent (e.g. 10 -> +/-10%).
        param_names: Optional subset of ``PARAM_NAMES`` to evaluate.

    Returns:
        Dict with keys ``baseline_lap_time`` [s], ``vehicle_id``,
        ``track_id``, ``pct`` and ``rows`` — a list of per-parameter
        dicts (name, description, baseline value, lap_minus, lap_plus,
        delta_minus, delta_plus, delta_abs) sorted by ``delta_abs``
        descending (tornado order).
    """
    specs = _build_param_specs()
    if param_names is not None:
        unknown = set(param_names) - {s.name for s in specs}
        if unknown:
            raise ValueError(f"Unknown parameters: {sorted(unknown)}. "
                             f"Available: {PARAM_NAMES}")
        specs = [s for s in specs if s.name in param_names]

    circuit = load_circuit(track_id)
    base_vp = load_vehicle(vehicle_id)
    baseline_lap = simulate_lap(base_vp, circuit, track_id).lap_time

    rows: List[Dict[str, Any]] = []
    for spec in specs:
        laps: Dict[str, float] = {}
        for label, scale in (("minus", 1.0 - pct / 100.0),
                             ("plus", 1.0 + pct / 100.0)):
            if spec.name in _SETUP_LEVEL_PARAMS:
                laps[label] = _lap_with_setup_param(
                    base_vp, circuit, track_id, spec.name, scale)
            else:
                vp = copy.deepcopy(base_vp)
                spec.setter(vp, spec.baseline(base_vp), scale)
                laps[label] = simulate_lap(vp, circuit, track_id).lap_time

        delta_minus = laps["minus"] - baseline_lap
        delta_plus = laps["plus"] - baseline_lap
        rows.append({
            "name": spec.name,
            "description": spec.description,
            "baseline_value": spec.baseline(base_vp),
            "lap_minus": laps["minus"],
            "lap_plus": laps["plus"],
            "delta_minus": delta_minus,
            "delta_plus": delta_plus,
            "delta_abs": max(abs(delta_minus), abs(delta_plus)),
        })

    rows.sort(key=lambda r: r["delta_abs"], reverse=True)
    return {
        "vehicle_id": vehicle_id,
        "track_id": track_id,
        "pct": pct,
        "baseline_lap_time": baseline_lap,
        "rows": rows,
    }


def _format_table(report: Dict[str, Any]) -> str:
    """Render the tornado table as aligned plain text."""
    header = (f"{'Parameter':<20} {'Baseline':>12} {'Lap -pct':>10} "
              f"{'Lap +pct':>10} {'d(-) [s]':>10} {'d(+) [s]':>10} "
              f"{'|dLap| [s]':>11}")
    lines = [header, "-" * len(header)]
    for r in report["rows"]:
        lines.append(
            f"{r['name']:<20} {r['baseline_value']:>12.4f} "
            f"{r['lap_minus']:>10.3f} {r['lap_plus']:>10.3f} "
            f"{r['delta_minus']:>+10.3f} {r['delta_plus']:>+10.3f} "
            f"{r['delta_abs']:>11.3f}"
        )
    return "\n".join(lines)


def save_report(report: Dict[str, Any]) -> Dict[str, str]:
    """Save the Markdown report and CSV table to ``src/results/``.

    Args:
        report: Output of :func:`run_sensitivity`.

    Returns:
        Dict with ``markdown`` and ``csv`` file paths.
    """
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = f"sensitivity_{report['vehicle_id']}_{report['track_id']}_{stamp}"
    csv_path = RESULTS_DIR / f"{stem}.csv"
    md_path = RESULTS_DIR / f"{stem}.md"

    df = pd.DataFrame(report["rows"])
    df.to_csv(csv_path, index=False)

    md = [
        f"# Sensitivity Analysis — {report['vehicle_id']} @ {report['track_id']}",
        "",
        f"- Date: {datetime.datetime.now().isoformat(timespec='seconds')}",
        f"- Perturbation: ±{report['pct']:.1f}% (OAT)",
        f"- Baseline lap time: **{report['baseline_lap_time']:.3f} s**",
        "",
        "| Parameter | Description | Baseline | Lap −pct [s] | Lap +pct [s] "
        "| Δ(−) [s] | Δ(+) [s] | max&#124;Δ&#124; [s] |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in report["rows"]:
        md.append(
            f"| {r['name']} | {r['description']} | {r['baseline_value']:.4f} "
            f"| {r['lap_minus']:.3f} | {r['lap_plus']:.3f} "
            f"| {r['delta_minus']:+.3f} | {r['delta_plus']:+.3f} "
            f"| {r['delta_abs']:.3f} |"
        )
    md += [
        "",
        "Tornado order: parameters sorted by the largest absolute lap-time "
        "swing. Setup-level parameters (tyre pressure, roll-stiffness split) "
        "are perturbed through the VehicleSetup layer; all other parameters "
        "through deep copies of VehicleParams. The 200 km/h governor is "
        "fixed by regulation and excluded by design.",
    ]
    md_path.write_text("\n".join(md), encoding="utf-8")
    return {"markdown": str(md_path), "csv": str(csv_path)}


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="OAT sensitivity analysis (tornado) for the LTS solver.")
    parser.add_argument("--vehicle", default="volkswagen_31320",
                        help="Fleet vehicle id (default: volkswagen_31320)")
    parser.add_argument("--track", default="cascavel",
                        help="Track id in tracks/*.hdf5 (default: cascavel)")
    parser.add_argument("--pct", type=float, default=10.0,
                        help="Perturbation amplitude in percent (default: 10)")
    parser.add_argument("--params", nargs="*", default=None,
                        help=f"Optional parameter subset of: {PARAM_NAMES}")
    parser.add_argument("--no-save", action="store_true",
                        help="Skip writing the Markdown/CSV report")
    args = parser.parse_args(argv)

    silence_solver_logging()
    report = run_sensitivity(args.vehicle, args.track, args.pct, args.params)

    print(f"\nBaseline lap ({args.vehicle} @ {args.track}): "
          f"{report['baseline_lap_time']:.3f} s — OAT ±{args.pct:.1f}%\n")
    print(_format_table(report))

    if not args.no_save:
        paths = save_report(report)
        print(f"\nReport : {paths['markdown']}")
        print(f"CSV    : {paths['csv']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
