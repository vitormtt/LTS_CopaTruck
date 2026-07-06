"""
Tests for the minimum-curvature racing line (src/tracks/racing_line.py).

The racing line replaces the naive centerline as the path the solver drives:
within the track boundaries it minimises curvature, so corners are taken on a
faster (lower-curvature) trajectory. Open methodology (TUM racetrack DB,
Veneri & Massaro 2019) — not proprietary.
"""
from __future__ import annotations

import numpy as np
import pytest

from src.tracks.racing_line import RacingLine, compute_racing_line


def _total_sq_curvature(x: np.ndarray, y: np.ndarray) -> float:
    dx = np.gradient(x)
    dy = np.gradient(y)
    ddx = np.gradient(dx)
    ddy = np.gradient(dy)
    k = (dx * ddy - dy * ddx) / (dx ** 2 + dy ** 2 + 1e-9) ** 1.5
    return float(np.sum(k ** 2))


def _straight(n: int = 50, width: float = 10.0):
    x = np.linspace(0.0, 500.0, n)
    y = np.zeros(n)
    left = np.column_stack([x, y + width / 2])
    right = np.column_stack([x, y - width / 2])
    center = np.column_stack([x, y])
    return center, left, right


def _arc(n: int = 120, radius: float = 80.0, width: float = 12.0):
    theta = np.linspace(0.0, np.pi, n)  # half circle
    cx = radius * np.cos(theta)
    cy = radius * np.sin(theta)
    # inward/outward normals (radial)
    nx, ny = np.cos(theta), np.sin(theta)
    left = np.column_stack([cx + nx * width / 2, cy + ny * width / 2])
    right = np.column_stack([cx - nx * width / 2, cy - ny * width / 2])
    center = np.column_stack([cx, cy])
    return center, left, right


def test_returns_racing_line_type():
    center, left, right = _straight()
    rl = compute_racing_line(center, left, right, closed=False)
    assert isinstance(rl, RacingLine)
    assert len(rl.x) == len(center)
    assert len(rl.alpha) == len(center)


def test_straight_track_stays_on_centerline():
    center, left, right = _straight()
    rl = compute_racing_line(center, left, right, closed=False)
    # No curvature to reduce -> line stays ~centered.
    assert np.max(np.abs(rl.alpha)) < 0.05
    assert np.allclose(rl.y, center[:, 1], atol=0.5)


def test_racing_line_stays_within_boundaries():
    center, left, right = _arc()
    rl = compute_racing_line(center, left, right, closed=False)
    assert np.all(rl.alpha <= 1.0 + 1e-6)
    assert np.all(rl.alpha >= -1.0 - 1e-6)


def test_real_track_racing_line_reduces_curvature():
    # Integration on the real closed Cascavel circuit (no synthetic pinned
    # ends): the racing line must reduce both total curvature energy and the
    # peak curvature (opens the tightest corner -> higher corner speed).
    import os

    from src.tracks.hdf5 import CircuitHDF5Reader

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    track = os.path.join(root, "tracks", "cascavel.hdf5")
    circuit, _ = CircuitHDF5Reader(track).read_circuit()
    center = np.column_stack([circuit.centerline_x, circuit.centerline_y])
    left = np.column_stack([circuit.left_boundary_x, circuit.left_boundary_y])
    right = np.column_stack([circuit.right_boundary_x, circuit.right_boundary_y])

    rl = compute_racing_line(center, left, right, closed=True)

    def curv(x, y):
        dx, dy = np.gradient(x), np.gradient(y)
        ddx, ddy = np.gradient(dx), np.gradient(dy)
        k = (dx * ddy - dy * ddx) / (dx ** 2 + dy ** 2 + 1e-9) ** 1.5
        return np.sum(k ** 2), np.max(np.abs(k))

    e_center, peak_center = curv(center[:, 0], center[:, 1])
    e_race, peak_race = curv(rl.x, rl.y)
    assert e_race < e_center
    assert peak_race < peak_center
    assert np.all(np.abs(rl.alpha) <= 1.0 + 1e-6)


def test_arc_racing_line_moves_off_center():
    center, left, right = _arc()
    rl = compute_racing_line(center, left, right, closed=False)
    # It should actually use the track width (apex), not sit on the centerline.
    assert np.max(np.abs(rl.alpha)) > 0.2


def test_closed_loop_is_periodic():
    theta = np.linspace(0.0, 2 * np.pi, 200, endpoint=False)
    r, width = 100.0, 14.0
    cx, cy = r * np.cos(theta), r * np.sin(theta)
    nx, ny = np.cos(theta), np.sin(theta)
    left = np.column_stack([cx + nx * width / 2, cy + ny * width / 2])
    right = np.column_stack([cx - nx * width / 2, cy - ny * width / 2])
    center = np.column_stack([cx, cy])
    rl = compute_racing_line(center, left, right, closed=True)
    # Endpoints must join smoothly on a closed loop.
    assert abs(rl.alpha[0] - rl.alpha[-1]) < 0.15
