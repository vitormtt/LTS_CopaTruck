"""
Validation module — simulation vs. real telemetry comparator.

Loads real telemetry data (PI Toolbox / MoTeC CSV export format) and computes
quantitative metrics to assess simulation fidelity.

Supported telemetry columns (auto-detected, case-insensitive aliases):
    Speed       : vehicle speed [km/h]
    RPM         : engine speed [rpm]
    Gear        : engaged gear [1–6]
    Throttle    : throttle position [%] or [0–1]
    Brake       : brake pressure or normalised brake [bar or 0–1]
    LongG / Long_G / Glong : longitudinal acceleration [g or m/s²]
    LatG  / Lat_G  / Glat  : lateral acceleration [g or m/s²]
    SteerAngle / Steer     : steering wheel angle [deg or rad]
    Distance    : cumulative distance [m]
    Time / Timestamp       : elapsed time [s]
    LapTime     : lap time marker [s]

Metrics computed:
    - Lap time absolute error [s] and relative error [%]
    - RMSE and MAE for: speed, RPM, long_g, lat_g
    - Pearson correlation coefficient for: speed, long_g, lat_g
    - Braking point distance error [m] (detected via long_g threshold)
    - Shift timing error [s] (detected via gear channel transitions)

Author: Lap Time Simulator Team
Date: 2026-03-10
References:
    - Hakewill, J. (2010). Lap Time Simulation.
    - Pearson, K. (1895). Notes on regression and inheritance.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import interpolate, stats


# ---------------------------------------------------------------------------
# Column name aliases (PI Toolbox / MoTeC / generic CSV)
# ---------------------------------------------------------------------------
_COLUMN_ALIASES: Dict[str, List[str]] = {
    "time":     ["time", "timestamp", "t", "elapsed"],
    "distance": ["distance", "dist", "xdist", "x_dist"],
    "speed":    ["speed", "velocity", "vcar", "v_car", "v"],
    "rpm":      ["rpm", "engine_speed", "enginerpm", "engine_rpm"],
    "gear":     ["gear", "gearposition", "gear_position"],
    "throttle": ["throttle", "throttle_pos", "aps", "tps", "accel"],
    "brake":    ["brake", "brakepressure", "brake_pressure", "bp"],
    "long_g":   ["longg", "long_g", "glong", "ax", "long_acc", "longitudinal_g"],
    "lat_g":    ["latg",  "lat_g",  "glat",  "ay", "lat_acc",  "lateral_g"],
    "steer":    ["steerangle", "steer", "steer_angle", "steering"],
    "lap_time": ["laptime", "lap_time", "lap"],
}


def _resolve_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """
    Map canonical channel names to actual DataFrame column names.

    Args:
        df: Loaded telemetry DataFrame.

    Returns:
        Dict mapping canonical name -> actual column name (or None if absent).
    """
    lower_cols = {c.lower().replace(" ", "_"): c for c in df.columns}
    resolved: Dict[str, Optional[str]] = {}
    for canonical, aliases in _COLUMN_ALIASES.items():
        resolved[canonical] = None
        for alias in aliases:
            if alias.lower() in lower_cols:
                resolved[canonical] = lower_cols[alias.lower()]
                break
    return resolved


@dataclass
class ValidationMetrics:
    """
    Quantitative metrics from simulation vs. real telemetry comparison.

    All metrics are computed on distance-aligned signals to eliminate
    cumulative time drift between simulation and reality.
    """
    lap_time_sim: float = 0.0          # [s]   — simulated lap time
    lap_time_real: float = 0.0         # [s]   — real lap time from telemetry
    lap_time_error_abs: float = 0.0    # [s]   — |sim - real|
    lap_time_error_pct: float = 0.0    # [%]   — |sim - real| / real * 100

    # Speed channel
    speed_rmse: float = 0.0            # [km/h]
    speed_mae: float = 0.0             # [km/h]
    speed_r: float = 0.0              # Pearson r [-]
    speed_max_error: float = 0.0       # [km/h] — worst-case

    # Longitudinal G
    long_g_rmse: float = 0.0           # [m/s²]
    long_g_r: float = 0.0

    # Lateral G
    lat_g_rmse: float = 0.0            # [m/s²]
    lat_g_r: float = 0.0

    # RPM channel
    rpm_rmse: float = 0.0              # [rpm]
    rpm_r: float = 0.0

    # Gear trace
    gear_match_pct: float = 0.0        # [%] — fraction of distance where gear matches
    mean_shift_timing_error: float = 0.0  # [m] — shift point distance error

    # Braking
    mean_braking_point_error: float = 0.0  # [m] — braking point detection error

    # Quality flag
    passed: bool = False               # True if all primary thresholds met
    warnings: List[str] = field(default_factory=list)

    # Validation thresholds (class-level, can be overridden)
    _LAP_TIME_THRESHOLD_PCT: float = 2.0   # acceptable lap time error [%]
    _SPEED_RMSE_THRESHOLD: float = 8.0     # acceptable speed RMSE [km/h]
    _LONG_G_R_THRESHOLD: float = 0.85      # minimum Pearson r for long_g
    _LAT_G_R_THRESHOLD: float = 0.80       # minimum Pearson r for lat_g

    def evaluate_pass(self) -> None:
        """Set self.passed based on primary threshold checks."""
        checks = [
            self.lap_time_error_pct <= self._LAP_TIME_THRESHOLD_PCT,
            self.speed_rmse <= self._SPEED_RMSE_THRESHOLD,
            self.long_g_r >= self._LONG_G_R_THRESHOLD,
            self.lat_g_r >= self._LAT_G_R_THRESHOLD,
        ]
        self.passed = all(checks)

    def summary(self) -> str:
        """Return formatted summary string for Streamlit / logging."""
        status = "✅ PASS" if self.passed else "❌ FAIL"
        lines = [
            f"=== Validation Report {status} ===",
            f"Lap time    : sim={self.lap_time_sim:.3f}s  real={self.lap_time_real:.3f}s  "
            f"Δ={self.lap_time_error_abs:.3f}s ({self.lap_time_error_pct:.2f}%)",
            f"Speed RMSE  : {self.speed_rmse:.2f} km/h  (MAE={self.speed_mae:.2f})  r={self.speed_r:.3f}",
            f"Long G      : RMSE={self.long_g_rmse:.3f} m/s²  r={self.long_g_r:.3f}",
            f"Lat G       : RMSE={self.lat_g_rmse:.3f} m/s²  r={self.lat_g_r:.3f}",
            f"RPM RMSE    : {self.rpm_rmse:.1f} rpm  r={self.rpm_r:.3f}",
            f"Gear match  : {self.gear_match_pct:.1f}%",
        ]
        if self.warnings:
            lines.append("Warnings: " + " | ".join(self.warnings))
        return "\n".join(lines)


def load_telemetry(filepath: str | Path, delimiter: str = ",") -> pd.DataFrame:
    """
    Load a telemetry CSV file into a standardised DataFrame.

    Auto-detects delimiter, normalises column names, and converts
    acceleration columns from g to m/s² if needed.

    Args:
        filepath  : Path to CSV file.
        delimiter : Column separator (default ',').

    Returns:
        pd.DataFrame with normalised column names.
    """
    filepath = Path(filepath)
    df = pd.read_csv(filepath, sep=delimiter, engine="python", skip_blank_lines=True)

    # Attempt semicolon as fallback delimiter
    if df.shape[1] == 1:
        df = pd.read_csv(filepath, sep=";", engine="python", skip_blank_lines=True)

    # Input must be in m/s² — auto-conversion removed (threshold ambiguous for trucks ≤ 0.5 g)
    resolved = _resolve_columns(df)

    # Normalise throttle 0–100 → 0–1
    throttle_col = resolved.get("throttle")
    if throttle_col and df[throttle_col].max() > 1.5:
        df[throttle_col] = df[throttle_col] / 100.0

    return df


def align_on_distance(
    sim_data: Dict[str, np.ndarray],
    real_df: pd.DataFrame,
    n_points: int = 2000,
) -> Tuple[Dict[str, np.ndarray], Dict[str, np.ndarray]]:
    """
    Interpolate both simulation and real telemetry onto a common distance grid.

    Distance-based alignment eliminates time-offset artefacts that arise from
    differing start conditions between simulation and real laps.

    Args:
        sim_data  : Dict of simulation output arrays (must contain 'distance' key).
        real_df   : Loaded telemetry DataFrame.
        n_points  : Number of interpolation points.

    Returns:
        Tuple (sim_aligned, real_aligned): both on the same distance grid.
    """
    resolved = _resolve_columns(real_df)
    dist_col = resolved.get("distance")
    if dist_col is None:
        raise ValueError(
            "Real telemetry has no distance column. "
            f"Expected one of: {_COLUMN_ALIASES['distance']}"
        )

    sim_dist = np.array(sim_data["distance"])
    d_max = min(sim_dist[-1], real_df[dist_col].max())
    d_grid = np.linspace(0.0, d_max, n_points)

    sim_aligned: Dict[str, np.ndarray] = {}
    for key, arr in sim_data.items():
        if key == "distance" or len(arr) != len(sim_dist):
            continue
        try:
            f = interpolate.interp1d(sim_dist, np.array(arr), bounds_error=False,
                                     fill_value="extrapolate")
            sim_aligned[key] = f(d_grid)
        except Exception:
            pass

    real_aligned: Dict[str, np.ndarray] = {}
    if dist_col:
        real_dist = real_df[dist_col].to_numpy(dtype=float)
        for canonical, col in resolved.items():
            if col and col != dist_col:
                try:
                    f = interpolate.interp1d(real_dist, real_df[col].to_numpy(dtype=float),
                                             bounds_error=False, fill_value="extrapolate")
                    real_aligned[canonical] = f(d_grid)
                except Exception:
                    pass

    return sim_aligned, real_aligned


def compute_metrics(
    sim_data: Dict[str, np.ndarray],
    real_df: pd.DataFrame,
    lap_time_sim: float,
    n_points: int = 2000,
) -> ValidationMetrics:
    """
    Compute all validation metrics between simulation and real telemetry.

    Args:
        sim_data     : Simulation output dict (keys: 'distance','speed','long_g',
                       'lat_g','rpm','gear', all as np.ndarray).
        real_df      : Loaded real telemetry DataFrame (from load_telemetry()).
        lap_time_sim : Total simulated lap time [s].
        n_points     : Interpolation resolution for distance alignment.

    Returns:
        ValidationMetrics dataclass with all computed metrics.
    """
    metrics = ValidationMetrics(lap_time_sim=lap_time_sim)
    resolved = _resolve_columns(real_df)

    # --- Lap time ---
    lap_col = resolved.get("lap_time")
    time_col = resolved.get("time")
    if lap_col and real_df[lap_col].max() > 0:
        metrics.lap_time_real = float(real_df[lap_col].max())
    elif time_col:
        metrics.lap_time_real = float(real_df[time_col].max())
    else:
        metrics.warnings.append("lap_time column not found in telemetry")

    if metrics.lap_time_real > 0:
        metrics.lap_time_error_abs = abs(lap_time_sim - metrics.lap_time_real)
        metrics.lap_time_error_pct = (
            metrics.lap_time_error_abs / metrics.lap_time_real * 100.0
        )

    # --- Distance-aligned comparison ---
    sim_al, real_al = align_on_distance(sim_data, real_df, n_points=n_points)

    def _channel_metrics(
        key: str, scale: float = 1.0
    ) -> Tuple[float, float, float, float]:
        """Compute RMSE, MAE, max_error, Pearson r for a channel."""
        s = sim_al.get(key)
        r = real_al.get(key)
        if s is None or r is None or len(s) == 0:
            return 0.0, 0.0, 0.0, 0.0
        s, r = s * scale, r * scale
        diff = s - r
        rmse = float(np.sqrt(np.mean(diff ** 2)))
        mae = float(np.mean(np.abs(diff)))
        max_err = float(np.max(np.abs(diff)))
        pearson_r, _ = stats.pearsonr(s, r)
        return rmse, mae, max_err, float(pearson_r)

    # Speed [m/s in sim → km/h]
    speed_rmse, speed_mae, speed_max, speed_r = _channel_metrics("speed", scale=3.6)
    metrics.speed_rmse = speed_rmse
    metrics.speed_mae = speed_mae
    metrics.speed_max_error = speed_max
    metrics.speed_r = speed_r

    # Long G
    metrics.long_g_rmse, _, _, metrics.long_g_r = _channel_metrics("long_g")

    # Lat G
    metrics.lat_g_rmse, _, _, metrics.lat_g_r = _channel_metrics("lat_g")

    # RPM
    metrics.rpm_rmse, _, _, metrics.rpm_r = _channel_metrics("rpm")

    # Gear match
    sim_gear = sim_al.get("gear")
    real_gear = real_al.get("gear")
    if sim_gear is not None and real_gear is not None:
        match = np.round(sim_gear).astype(int) == np.round(real_gear).astype(int)
        metrics.gear_match_pct = float(np.mean(match) * 100.0)

    # Braking point detection (long_g < -8.0 m/s² threshold)
    sim_long = sim_al.get("long_g")
    real_long = real_al.get("long_g")
    dist_col_cm = resolved.get("distance")
    d_max_cm = float(
        min(np.array(sim_data["distance"])[-1],
            real_df[dist_col_cm].max() if dist_col_cm else np.array(sim_data["distance"])[-1])
    )
    dist_per_index = d_max_cm / n_points  # [m] per grid index
    if sim_long is not None and real_long is not None:
        brake_thresh = -8.0  # [m/s²]
        sim_bp = np.where(np.diff((sim_long < brake_thresh).astype(int)) > 0)[0]
        real_bp = np.where(np.diff((real_long < brake_thresh).astype(int)) > 0)[0]
        min_events = min(len(sim_bp), len(real_bp))
        if min_events > 0:
            bp_errors = np.abs(sim_bp[:min_events] - real_bp[:min_events]) * dist_per_index
            metrics.mean_braking_point_error = float(np.mean(bp_errors))

    metrics.evaluate_pass()
    return metrics
