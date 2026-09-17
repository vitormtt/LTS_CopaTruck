"""
Tests for Telios-style race-report analytics (src/analysis/race_report.py).

Pure-math layer: grip factors, G-G envelope, sector deltas across laps and
per-lap KPI extraction. Session I/O (.xrk) is a boundary and is not tested
here.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.analysis.race_report import (
    GripFactors,
    grip_factors,
    lap_kpis,
    sector_deltas,
)


def _lap_df(v_kmh: float = 144.0, n: int = 200, length: float = 3000.0,
            ax_amp: float = 0.8, ay_amp: float = 1.2) -> pd.DataFrame:
    d = np.linspace(0.0, length, n)
    phase = np.linspace(0.0, 4 * np.pi, n)
    return pd.DataFrame({
        "distance_m": d,
        "v_kmh": np.full(n, v_kmh) + 10 * np.sin(phase),
        "ax_long_g": ax_amp * np.sin(phase),          # braking<0 / accel>0
        "ay_lat_g": ay_amp * np.cos(phase),
    })


def test_grip_factors_signs_and_magnitudes():
    df = _lap_df(ax_amp=0.8, ay_amp=1.2)
    gf = grip_factors(df)
    assert isinstance(gf, GripFactors)
    # Braking = mean of |ax| where ax < threshold -> positive number.
    assert 0.3 < gf.braking_g < 0.9
    assert 0.3 < gf.accel_g < 0.9
    assert 0.6 < gf.cornering_g < 1.3
    assert gf.overall_g > gf.cornering_g * 0.5  # combined magnitude sane


def test_grip_factors_zero_channels():
    df = _lap_df(ax_amp=0.0, ay_amp=0.0)
    gf = grip_factors(df)
    assert gf.braking_g == pytest.approx(0.0, abs=1e-9)
    assert gf.accel_g == pytest.approx(0.0, abs=1e-9)
    assert gf.cornering_g == pytest.approx(0.0, abs=1e-9)


def test_lap_kpis_basic():
    df = _lap_df(v_kmh=150.0)
    k = lap_kpis(df, lap_time_s=80.0)
    assert k["lap_time_s"] == pytest.approx(80.0)
    assert 140.0 < k["top_speed_kmh"] <= 165.0
    assert k["mean_ay_max_g"] > 0.5


def test_sector_deltas_identical_laps_zero():
    ref = _lap_df()
    laps = [ref.copy(), ref.copy(), ref.copy()]
    table = sector_deltas(laps, [80.0, 80.0, 80.0], n_sectors=3)
    # Identical speed traces -> zero delta everywhere.
    assert set(table.columns) == {"lap", "sector", "delta_s"}
    assert np.allclose(table["delta_s"], 0.0, atol=1e-9)
    assert sorted(table["sector"].unique()) == ["S1", "S2", "S3"]


def test_sector_deltas_slower_sector_positive():
    ref = _lap_df(v_kmh=150.0)
    slow = ref.copy()
    n = len(slow)
    # Make sector 2 (middle third by distance) slower on lap 2.
    third = slow["distance_m"] > slow["distance_m"].iloc[-1] / 3
    two_thirds = slow["distance_m"] <= 2 * slow["distance_m"].iloc[-1] / 3
    slow.loc[third & two_thirds, "v_kmh"] -= 20.0
    table = sector_deltas([ref, slow], [80.0, 82.0], n_sectors=3)
    s2 = table[(table["lap"] == 2) & (table["sector"] == "S2")]["delta_s"].iloc[0]
    s1 = table[(table["lap"] == 2) & (table["sector"] == "S1")]["delta_s"].iloc[0]
    assert s2 > 0.05          # slower mid sector shows positive delta
    assert abs(s1) < 0.05     # untouched sector unchanged
