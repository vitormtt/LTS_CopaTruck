"""
Sim-vs-reference telemetry overlay.

Compares a simulated speed-vs-distance trace against a reference lap
(CSV with ``distance_m`` and ``v_kmh`` columns — the native format of the
.xrk converter pipeline and of the simulator CSV export). Produces the
delta channels a race engineer reads first: Δv(d), cumulative Δt(d),
RMSE and lap time deltas.

Validation principle (Perantoni & Limebeer): compare the full speed trace
by distance, not just the lap time — two errors can cancel in the lap.

Pure NumPy/pandas — no Streamlit imports (UI lives in
src/visualization/components/overlay.py).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import IO, Union

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = ("distance_m", "v_kmh")
_MIN_SPEED_MS = 1.0  # floor to avoid div-by-zero when integrating ds/v
_GRID_STEP_M = 5.0   # common-distance resample step


@dataclass(frozen=True)
class OverlayResult:
    """Delta channels and scalar metrics of a sim-vs-reference overlay."""
    grid_m: np.ndarray        # common distance grid [m]
    sim_v_kmh: np.ndarray     # sim speed on grid [km/h]
    ref_v_kmh: np.ndarray     # reference speed on grid [km/h]
    delta_v_kmh: np.ndarray   # sim - ref [km/h]
    delta_time_s: np.ndarray  # cumulative time delta sim - ref [s]
    rmse_kmh: float           # speed RMSE over the grid [km/h]
    sim_time_s: float         # sim segment time over the grid [s]
    ref_time_s: float         # reference segment time over the grid [s]


def load_reference_csv(source: Union[str, IO]) -> pd.DataFrame:
    """Load a reference lap CSV requiring ``distance_m`` and ``v_kmh``.

    Args:
        source: File path or file-like object (e.g. Streamlit upload).

    Returns:
        DataFrame with the two required columns, NaN-free, sorted by
        distance.

    Raises:
        ValueError: If required columns are missing or no rows survive.
    """
    df = pd.read_csv(source)
    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(
            f"Reference CSV missing columns {sorted(missing)}; expected "
            "'distance_m' and 'v_kmh'."
        )
    df = df[list(REQUIRED_COLUMNS)].dropna().sort_values("distance_m")
    if df.empty:
        raise ValueError("Reference CSV has no valid rows.")
    return df.reset_index(drop=True)


def _segment_time(grid: np.ndarray, v_kmh: np.ndarray) -> np.ndarray:
    """Cumulative time [s] along the grid integrating ds/v."""
    v_ms = np.maximum(v_kmh / 3.6, _MIN_SPEED_MS)
    ds = np.diff(grid, prepend=grid[0])
    # trapezoidal-ish: use midpoint speed between consecutive samples
    v_mid = np.concatenate([[v_ms[0]], (v_ms[1:] + v_ms[:-1]) / 2.0])
    return np.cumsum(ds / v_mid)


def compute_overlay(
    sim_distance_m: np.ndarray,
    sim_v_kmh: np.ndarray,
    reference: pd.DataFrame,
) -> OverlayResult:
    """Resample sim and reference onto a common grid and compute deltas.

    Args:
        sim_distance_m: Simulated distance channel [m].
        sim_v_kmh: Simulated speed channel [km/h].
        reference: DataFrame from :func:`load_reference_csv`.

    Returns:
        OverlayResult with delta channels and scalar metrics.

    Raises:
        ValueError: If the traces do not overlap in distance.
    """
    sim_d = np.asarray(sim_distance_m, dtype=float)
    sim_v = np.asarray(sim_v_kmh, dtype=float)
    ref_d = reference["distance_m"].to_numpy(dtype=float)
    ref_v = reference["v_kmh"].to_numpy(dtype=float)

    lo = max(sim_d.min(), ref_d.min())
    hi = min(sim_d.max(), ref_d.max())
    if hi <= lo:
        raise ValueError(
            "Simulated and reference laps do not overlap in distance "
            f"(sim [{sim_d.min():.0f}, {sim_d.max():.0f}] m vs "
            f"ref [{ref_d.min():.0f}, {ref_d.max():.0f}] m)."
        )

    n = max(int((hi - lo) / _GRID_STEP_M), 2)
    grid = np.linspace(lo, hi, n)
    sim_i = np.interp(grid, sim_d, sim_v)
    ref_i = np.interp(grid, ref_d, ref_v)
    delta_v = sim_i - ref_i

    t_sim = _segment_time(grid, sim_i)
    t_ref = _segment_time(grid, ref_i)

    return OverlayResult(
        grid_m=grid,
        sim_v_kmh=sim_i,
        ref_v_kmh=ref_i,
        delta_v_kmh=delta_v,
        delta_time_s=t_sim - t_ref,
        rmse_kmh=float(np.sqrt(np.mean(delta_v ** 2))),
        sim_time_s=float(t_sim[-1]),
        ref_time_s=float(t_ref[-1]),
    )
