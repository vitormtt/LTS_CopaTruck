"""Pacejka Magic Formula design curves (Fx, Fy, Mz, Mx, My).

Design-view companion to the tyre section of the vehicle-parameters page:
given the four MF scalars stored in ``TireParams`` (B, C, D, E — lateral
base) and a reference vertical load, it produces the characteristic force
and moment curves an engineer inspects to judge whether the coefficient
set is physically sensible.

NOTE: the lap solver still runs the LINEAR friction-circle model; these
curves are project visualisation only (wiring Pacejka into the solver is a
separate, cross-validated change — golden rule #2).

Reference: Pacejka, H. B. (2012). *Tire and Vehicle Dynamics*, 3rd ed.,
ch. 4 (Magic Formula). Auxiliary shape constants below follow the typical
published ratios between longitudinal, lateral and aligning behaviour.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Domain limits for the design plots
SLIP_ANGLE_MAX_DEG = 12.0   # lateral slip sweep [deg]
SLIP_RATIO_MAX = 0.30       # longitudinal slip sweep [-]
_N_POINTS = 201

# Typical MF shape ratios (Pacejka 2012, tables 4.1-4.2):
# longitudinal curves are stiffer and rounder than lateral ones.
_LONG_STIFFNESS_RATIO = 1.25   # Bx / By
_LONG_SHAPE_C = 1.65           # Cx (lateral C is user input, ~1.3)
# Aligning moment: pneumatic trail peaks at ~2.5-3.5% of tyre radius and
# decays faster than Fy (higher shape factor).
_TRAIL_PEAK_FRACTION = 0.03    # t0 / R_wheel
_TRAIL_SHAPE_C = 2.4
# Overturning moment lever as a fraction of wheel radius (tall 295/80
# truck sidewall shifts the contact patch laterally under slip).
_OVERTURNING_LEVER_FRACTION = 0.07
# Rolling resistance coefficient band for a hot truck racing radial
_ROLLING_RESISTANCE_COEFF = 0.008


@dataclass(frozen=True)
class TireCurves:
    """Characteristic MF curves over the slip sweeps (design view)."""

    slip_ratio: np.ndarray      # [-] domain for Fx, My
    slip_angle_deg: np.ndarray  # [deg] domain for Fy, Mz, Mx
    fx: np.ndarray              # longitudinal force [N]
    fy: np.ndarray              # lateral force [N]
    mz: np.ndarray              # aligning moment [Nm]
    mx: np.ndarray              # overturning moment [Nm]
    my: np.ndarray              # rolling-resistance moment [Nm] (vs slip ratio)


def magic_formula(x: np.ndarray, b: float, c: float, d: float, e: float) -> np.ndarray:
    """Base Magic Formula y(x) = D·sin(C·atan(Bx − E(Bx − atan(Bx)))).

    Args:
        x: Slip quantity (ratio [-] or angle [rad]).
        b: Stiffness factor.
        c: Shape factor.
        d: Peak value.
        e: Curvature factor.

    Returns:
        Force/moment values, same shape as ``x``.
    """
    bx = b * np.asarray(x, dtype=float)
    return d * np.sin(c * np.arctan(bx - e * (bx - np.arctan(bx))))


def tire_curves(
    mu: float,
    fz_n: float,
    wheel_radius_m: float,
    b: float,
    c: float,
    d: float,
    e: float,
) -> TireCurves:
    """Build the five MF design curves for one tyre at a reference load.

    Args:
        mu: Peak friction coefficient [-].
        fz_n: Reference vertical load on the tyre [N].
        wheel_radius_m: Rolling radius [m] (scales the moment levers).
        b: MF stiffness factor (lateral base).
        c: MF shape factor (lateral).
        d: MF peak factor (normalised; peak force = mu*d*fz).
        e: MF curvature factor.

    Returns:
        TireCurves with Fx(κ), Fy(α), Mz(α), Mx(α) and My(κ).

    Raises:
        ValueError: If ``fz_n`` or ``wheel_radius_m`` is not positive.
    """
    if fz_n <= 0.0:
        raise ValueError("fz_n must be positive.")
    if wheel_radius_m <= 0.0:
        raise ValueError("wheel_radius_m must be positive.")

    kappa = np.linspace(-SLIP_RATIO_MAX, SLIP_RATIO_MAX, _N_POINTS)
    alpha_deg = np.linspace(-SLIP_ANGLE_MAX_DEG, SLIP_ANGLE_MAX_DEG, _N_POINTS)
    alpha_rad = np.radians(alpha_deg)

    peak_force = mu * d * fz_n

    fx = magic_formula(kappa, b * _LONG_STIFFNESS_RATIO, _LONG_SHAPE_C,
                       peak_force, e)
    fy = magic_formula(alpha_rad, b, c, peak_force, e)

    # Aligning moment: Mz = -trail(α) · Fy(α); trail decays with slip.
    trail0 = _TRAIL_PEAK_FRACTION * wheel_radius_m
    trail = trail0 * magic_formula(alpha_rad, b, _TRAIL_SHAPE_C, 1.0, e)
    mz = -trail * fy

    # Overturning moment grows with lateral force (tall sidewall lever).
    mx = -_OVERTURNING_LEVER_FRACTION * wheel_radius_m * fy

    # Rolling resistance moment (constant magnitude, opposes rolling).
    my = np.full_like(kappa, -_ROLLING_RESISTANCE_COEFF * fz_n * wheel_radius_m)

    return TireCurves(slip_ratio=kappa, slip_angle_deg=alpha_deg,
                      fx=fx, fy=fy, mz=mz, mx=mx, my=my)
