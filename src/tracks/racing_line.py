"""
Minimum-curvature racing line.

The point-mass QSS solver historically drove the track **centerline**, which
is not the fast path: real drivers cut corners on a lower-curvature line
inside the track boundaries. This module computes that line by minimising the
integrated squared curvature of the path, constrained to stay within the
track edges.

Method (open, non-proprietary — TUM racetrack-database / Heilmeier et al.
2019; Veneri & Massaro 2019): parametrise each path point as a lateral offset
from the centerline,

    P_i = C_i + alpha_i * hw_i * n_i,   alpha_i in [-1, 1]

with ``n_i`` the centerline unit normal and ``hw_i`` the local half-width. The
path is linear in ``alpha`` so minimising the discrete second-difference
energy ||P_{i-1} - 2 P_i + P_{i+1}||^2 (a convex proxy for curvature) is a
bounded quadratic program, solved here by projected gradient descent
(O(N) per iteration, scales to thousands of points).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import sparse
from scipy.optimize import lsq_linear


@dataclass(frozen=True)
class RacingLine:
    """A computed racing line.

    Attributes:
        x: Path x coordinates [m].
        y: Path y coordinates [m].
        alpha: Lateral offset per point, -1 (right edge) .. +1 (left edge).
        half_width: Local half-width used per point [m].
    """
    x: np.ndarray
    y: np.ndarray
    alpha: np.ndarray
    half_width: np.ndarray


def _unit_normals(center: np.ndarray, closed: bool) -> np.ndarray:
    """Left-pointing unit normals along the centerline."""
    if closed:
        tangent = np.roll(center, -1, axis=0) - np.roll(center, 1, axis=0)
    else:
        tangent = np.gradient(center, axis=0)
    norm = np.hypot(tangent[:, 0], tangent[:, 1]) + 1e-12
    tx, ty = tangent[:, 0] / norm, tangent[:, 1] / norm
    # Rotate tangent +90 deg -> left normal.
    return np.column_stack([-ty, tx])


def _second_difference_operator(n: int, closed: bool) -> sparse.csr_matrix:
    """Sparse discrete second-difference operator D (N x N)."""
    main = -2.0 * np.ones(n)
    off = np.ones(n - 1)
    D = sparse.diags([off, main, off], [-1, 0, 1], format="lil")
    if closed:
        D[0, n - 1] = 1.0
        D[n - 1, 0] = 1.0
    else:
        # Open segment: zero the second difference at the free endpoints.
        D[0, :] = 0.0
        D[n - 1, :] = 0.0
    return D.tocsr()


def compute_racing_line(
    center: np.ndarray,
    left: np.ndarray,
    right: np.ndarray,
    closed: bool = True,
    vehicle_width_m: float = 0.0,
) -> RacingLine:
    """Compute the minimum-curvature racing line within the track boundaries.

    Args:
        center: Centerline points, shape (N, 2).
        left: Left boundary points, shape (N, 2).
        right: Right boundary points, shape (N, 2).
        closed: True for a closed circuit (periodic), False for an open segment.
        vehicle_width_m: Vehicle width [m]; the usable corridor shrinks by
            half of it on each side, so a wide truck gets a different (and
            slower) optimal line than a narrow single-seater. 0 = point-width.

    Returns:
        RacingLine with the path, per-point lateral offset and half-width.

    Raises:
        ValueError: If the inputs do not share the same length or are too short.
    """
    center = np.asarray(center, dtype=float)
    left = np.asarray(left, dtype=float)
    right = np.asarray(right, dtype=float)
    n = len(center)
    if not (len(left) == len(right) == n):
        raise ValueError("center, left and right must have equal length.")
    if n < 3:
        raise ValueError("Need at least 3 points to compute a racing line.")

    normals = _unit_normals(center, closed)
    # Local half-width available toward each edge; use the smaller so the line
    # never crosses either boundary when |alpha| = 1.
    hw_left = np.hypot(*(left - center).T)
    hw_right = np.hypot(*(right - center).T)
    half_width = np.minimum(hw_left, hw_right)
    half_width = np.maximum(half_width, 1e-6)

    offset_dir = normals * half_width[:, None]  # P = C + alpha * offset_dir

    # Minimise ||D (C + diag(offset)·alpha)||^2 over alpha in [-1, 1]. Linear in
    # alpha, so this is a bounded least-squares (convex QP):
    #     A·alpha ≈ -b,  A = [D·diag(off_x); D·diag(off_y)],  b = [D·Cx; D·Cy].
    D = _second_difference_operator(n, closed)
    A = sparse.vstack([
        D @ sparse.diags(offset_dir[:, 0]),
        D @ sparse.diags(offset_dir[:, 1]),
    ]).tocsr()
    b = np.concatenate([D @ center[:, 0], D @ center[:, 1]])

    # Shrink the usable corridor by half the vehicle width on each side
    # (doc "Validação de Lap Sim": track limits must be discounted by the
    # vehicle's structural width). Cap the margin so a too-narrow track never
    # inverts the bounds — the line degrades toward the centerline there.
    margin = np.clip((vehicle_width_m / 2.0) / half_width, 0.0, 0.95)
    bound = 1.0 - margin
    sol = lsq_linear(A, -b, bounds=(-bound, bound), max_iter=200)
    alpha = sol.x
    if not closed:
        alpha[0] = alpha[-1] = 0.0  # pin free-segment ends to the centerline

    path = center + alpha[:, None] * offset_dir
    return RacingLine(x=path[:, 0], y=path[:, 1], alpha=alpha,
                      half_width=half_width)
