"""
Telios-style race-report analytics.

Pure computation layer for the Race Report page: per-lap KPIs, grip
factors (braking / cornering / accel / overall, in G), sector deltas
across the laps of a session, and .xrk session extraction with the REAL
channels of the Copa Truck loggers (Freio_Press, Ped, Combustivel,
InlineAcc/LateralAcc, GPS Speed).

What is deliberately NOT here (no data in the current .xrk loggers —
flagged in the UI instead of faked):
- damper velocity histograms (no damper pots logged);
- tyre pressure per corner over laps (no TPMS channel);
- pitch angle vs Ax (only PitchRate is logged; integration drifts).

References: standard race-engineering KPI practice (MoTeC/Pi Toolbox
reports); grip factors as mean |G| per dynamic regime.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

# Regime thresholds [G] — below these the channel is coasting noise.
_BRAKE_G_MIN = 0.10
_ACCEL_G_MIN = 0.05
_CORNER_G_MIN = 0.20
# A lap is "valid" when its duration sits within this band of the best.
_VALID_LAP_FACTOR = 1.35
_MIN_LAP_S = 40.0


@dataclass(frozen=True)
class GripFactors:
    """Mean grip usage per dynamic regime [G]."""
    braking_g: float
    cornering_g: float
    accel_g: float
    overall_g: float


def grip_factors(lap: pd.DataFrame) -> GripFactors:
    """Compute mean grip factors of one lap from ax/ay channels.

    Args:
        lap: DataFrame with ``ax_long_g`` and ``ay_lat_g`` columns.

    Returns:
        GripFactors with mean |G| per regime (0.0 when a regime never occurs).
    """
    ax = lap["ax_long_g"].to_numpy(dtype=float)
    ay = lap["ay_lat_g"].to_numpy(dtype=float)

    braking = -ax[ax < -_BRAKE_G_MIN]
    accel = ax[ax > _ACCEL_G_MIN]
    corner = np.abs(ay[np.abs(ay) > _CORNER_G_MIN])
    combined = np.hypot(ax, ay)

    def _mean(arr: np.ndarray) -> float:
        return float(np.mean(arr)) if len(arr) else 0.0

    return GripFactors(
        braking_g=_mean(braking),
        cornering_g=_mean(corner),
        accel_g=_mean(accel),
        overall_g=_mean(combined[combined > _CORNER_G_MIN]),
    )


def lap_kpis(lap: pd.DataFrame, lap_time_s: float) -> dict:
    """Per-lap KPI row (Telios summary-table style).

    Args:
        lap: Lap DataFrame with ``v_kmh`` (+ optional ``fuel_l`` cumulative).
        lap_time_s: Lap duration [s].

    Returns:
        Dict with lap_time_s, top_speed_kmh, mean_speed_kmh, mean_ay_max_g
        and fuel_l when available.
    """
    v = lap["v_kmh"].to_numpy(dtype=float)
    out = {
        "lap_time_s": float(lap_time_s),
        "top_speed_kmh": float(np.max(v)) if len(v) else 0.0,
        "mean_speed_kmh": float(np.mean(v)) if len(v) else 0.0,
    }
    if "ay_lat_g" in lap:
        ay = np.abs(lap["ay_lat_g"].to_numpy(dtype=float))
        # Mean of the top-decile lateral peaks — robust "Ay max" metric.
        top = np.quantile(ay, 0.9) if len(ay) else 0.0
        out["mean_ay_max_g"] = float(np.mean(ay[ay >= top])) if len(ay) else 0.0
    if "fuel_l" in lap and lap["fuel_l"].notna().any():
        f = lap["fuel_l"].to_numpy(dtype=float)
        out["fuel_l"] = float(abs(f[-1] - f[0]))
    return out


def sector_deltas(
    laps: list[pd.DataFrame],
    lap_times_s: list[float],
    n_sectors: int = 3,
) -> pd.DataFrame:
    """Sector time deltas of each lap vs the session-best lap.

    Sectors are equal distance splits (S1..Sn). Sector time is integrated
    as ds/v over the lap's own distance channel, so laps of slightly
    different logged length still compare on their common span.

    Args:
        laps: One DataFrame per lap (``distance_m``, ``v_kmh``).
        lap_times_s: Duration of each lap [s] (defines the reference lap).
        n_sectors: Number of equal-distance sectors.

    Returns:
        Long-form DataFrame: columns ``lap`` (1-based), ``sector`` ("S1"...),
        ``delta_s`` (positive = slower than reference).
    """
    if not laps:
        return pd.DataFrame(columns=["lap", "sector", "delta_s"])

    ref_idx = int(np.argmin(lap_times_s))

    def _sector_times(lap: pd.DataFrame) -> np.ndarray:
        d = lap["distance_m"].to_numpy(dtype=float)
        v = np.maximum(lap["v_kmh"].to_numpy(dtype=float) / 3.6, 1.0)
        rel = (d - d[0]) / max(d[-1] - d[0], 1e-9)
        times = np.zeros(n_sectors)
        ds = np.diff(d, prepend=d[0])
        seg_t = ds / v
        for k in range(n_sectors):
            mask = (rel >= k / n_sectors) & (rel < (k + 1) / n_sectors)
            times[k] = float(np.sum(seg_t[mask]))
        return times

    ref_times = _sector_times(laps[ref_idx])
    rows = []
    for i, lap in enumerate(laps):
        deltas = _sector_times(lap) - ref_times
        for k in range(n_sectors):
            rows.append({"lap": i + 1, "sector": f"S{k + 1}",
                         "delta_s": float(deltas[k])})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# .xrk session extraction (boundary — uses libxrk, not unit-tested)
# ---------------------------------------------------------------------------

# AiM channel names seen in the Copa Truck loggers -> canonical channels.
_SESSION_CHANNELS = {
    "GPS Speed": "v_ms",
    "InlineAcc": "ax_long_g",
    "LateralAcc": "ay_lat_g",
    "RPM": "rpm",
    "Ped": "throttle_pct",
    "Freio_Press": "brake_press",
    "Combustivel": "fuel_l",
    "YawRate": "yaw_rate",
}


def extract_session(xrk_path: str) -> tuple[list[pd.DataFrame], list[float], dict]:
    """Extract all valid laps of an .xrk session with real channels.

    A lap is valid when longer than ``_MIN_LAP_S`` and within
    ``_VALID_LAP_FACTOR`` of the session best (drops in/out laps).

    Args:
        xrk_path: Path to the AiM .xrk file.

    Returns:
        (laps, lap_times, meta): one resampled DataFrame per valid lap
        (distance_m, v_kmh + whatever real channels exist), durations [s]
        and session metadata.
    """
    from libxrk import aim_xrk

    log = aim_xrk(xrk_path)
    laps_tbl = log.laps.to_pandas()
    laps_tbl["dur"] = (laps_tbl["end_time"] - laps_tbl["start_time"]) / 1000.0
    plausible = laps_tbl[laps_tbl["dur"] > _MIN_LAP_S]
    if plausible.empty:
        return [], [], dict(log.metadata)
    best = plausible["dur"].min()
    valid = plausible[plausible["dur"] <= best * _VALID_LAP_FACTOR]

    laps: list[pd.DataFrame] = []
    times: list[float] = []
    for row in valid.itertuples():
        lap_log = log.filter_by_lap(int(row.num))
        df = lap_log.get_channels_as_table().to_pandas()
        df = df.sort_values("timecodes").reset_index(drop=True)
        t = (df["timecodes"] - df["timecodes"].iloc[0]).to_numpy(dtype=float) / 1000.0

        out = pd.DataFrame({"time_s": t})
        for aim_name, canon in _SESSION_CHANNELS.items():
            if aim_name in df.columns:
                out[canon] = pd.to_numeric(df[aim_name], errors="coerce")
        if "v_ms" not in out:
            continue
        out["v_ms"] = out["v_ms"].ffill().fillna(0.0)
        out["v_kmh"] = out["v_ms"] * 3.6
        dt = np.diff(t, prepend=0.0)
        out["distance_m"] = np.cumsum(out["v_ms"].to_numpy() * dt)
        out = out.drop(columns=["v_ms"])
        # Forward-fill slow channels sampled below GPS rate.
        out = out.ffill()
        laps.append(out)
        times.append(float(row.dur))

    return laps, times, dict(log.metadata)
