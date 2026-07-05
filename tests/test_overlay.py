"""
Tests for sim-vs-reference telemetry overlay (src/analysis/overlay.py).

Reference format: CSV with ``distance_m`` and ``v_kmh`` columns — native
output of the .xrk converter pipeline and of the simulator CSV export.
"""
from __future__ import annotations

import io

import numpy as np
import pandas as pd
import pytest

from src.analysis.overlay import (
    OverlayResult,
    compute_overlay,
    load_reference_csv,
    split_laps,
)


def _ref_csv(dist: np.ndarray, v: np.ndarray) -> io.StringIO:
    return io.StringIO(
        pd.DataFrame({"distance_m": dist, "v_kmh": v}).to_csv(index=False)
    )


def test_load_reference_csv_valid():
    buf = _ref_csv(np.array([0.0, 100.0, 200.0]), np.array([100.0, 150.0, 120.0]))
    df = load_reference_csv(buf)
    assert list(df.columns) == ["distance_m", "v_kmh"]
    assert len(df) == 3


def test_load_reference_csv_missing_column_raises():
    buf = io.StringIO("distance_m,speed\n0,100\n")
    with pytest.raises(ValueError, match="v_kmh"):
        load_reference_csv(buf)


def test_identical_traces_zero_delta():
    dist = np.linspace(0.0, 1000.0, 101)
    v = np.full_like(dist, 144.0)  # 40 m/s constant
    ref = pd.DataFrame({"distance_m": dist, "v_kmh": v})
    res = compute_overlay(dist, v, ref)
    assert isinstance(res, OverlayResult)
    assert res.rmse_kmh == pytest.approx(0.0, abs=1e-9)
    assert np.allclose(res.delta_v_kmh, 0.0)
    # 1000 m at 40 m/s = 25 s on both sides
    assert res.sim_time_s == pytest.approx(25.0, rel=1e-3)
    assert res.ref_time_s == pytest.approx(25.0, rel=1e-3)
    assert res.delta_time_s[-1] == pytest.approx(0.0, abs=1e-6)


def test_slower_sim_positive_time_delta():
    dist = np.linspace(0.0, 1000.0, 101)
    v_ref = np.full_like(dist, 144.0)   # 40 m/s
    v_sim = np.full_like(dist, 129.6)   # 36 m/s → slower
    ref = pd.DataFrame({"distance_m": dist, "v_kmh": v_ref})
    res = compute_overlay(dist, v_sim, ref)
    assert res.rmse_kmh == pytest.approx(14.4, rel=1e-6)
    # sim loses time: cumulative delta (sim - ref) ends positive
    assert res.delta_time_s[-1] > 0.5
    assert res.sim_time_s > res.ref_time_s


def test_load_reference_csv_accepts_distance_alias():
    # .xrk converter output uses 'distance' instead of 'distance_m'
    buf = io.StringIO("distance,v_kmh\n0,100\n100,150\n200,120\n")
    df = load_reference_csv(buf)
    assert list(df.columns) == ["distance_m", "v_kmh"]
    assert len(df) == 3


def test_load_reference_csv_accepts_speed_alias():
    buf = io.StringIO("distance_m,speed_kmh\n0,100\n100,150\n")
    df = load_reference_csv(buf)
    assert df["v_kmh"].iloc[1] == pytest.approx(150.0)


def test_split_laps_single_lap_passthrough():
    df = pd.DataFrame({
        "distance_m": np.linspace(0, 3000, 31),
        "v_kmh": np.full(31, 120.0),
    })
    laps = split_laps(df)
    assert len(laps) == 1
    assert len(laps[0]) == 31


def test_split_laps_detects_distance_resets():
    # 3 laps concatenated: distance resets to ~0 at each lap start
    one = np.linspace(0, 3000, 31)
    df = pd.DataFrame({
        "distance_m": np.concatenate([one, one, one]),
        "v_kmh": np.concatenate([
            np.full(31, 120.0),   # lap 1 slow
            np.full(31, 150.0),   # lap 2 fast
            np.full(31, 130.0),   # lap 3 mid
        ]),
    })
    laps = split_laps(df)
    assert len(laps) == 3
    assert all(len(lap) == 31 for lap in laps)
    # each split lap starts near zero distance
    assert all(lap["distance_m"].iloc[0] == pytest.approx(0.0) for lap in laps)


def test_split_laps_ignores_tiny_fragments():
    # A 2-sample fragment (out-lap tail) should be dropped
    full = np.linspace(0, 3000, 31)
    frag = np.array([0.0, 90.0])
    df = pd.DataFrame({
        "distance_m": np.concatenate([frag, full]),
        "v_kmh": np.full(33, 120.0),
    })
    laps = split_laps(df)
    assert len(laps) == 1
    assert len(laps[0]) == 31


def test_non_overlapping_traces_raise():
    dist_sim = np.linspace(0.0, 100.0, 11)
    v_sim = np.full_like(dist_sim, 100.0)
    ref = pd.DataFrame({
        "distance_m": np.linspace(5000.0, 6000.0, 11),
        "v_kmh": np.full(11, 100.0),
    })
    with pytest.raises(ValueError, match="overlap"):
        compute_overlay(dist_sim, v_sim, ref)
