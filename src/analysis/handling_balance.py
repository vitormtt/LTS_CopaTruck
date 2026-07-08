"""
Handling-balance analysis — per-axle grip utilisation and under/oversteer.

Makes Roll Stiffness Distribution (RSD) *visible*: shows, at every cornering
point, how close each axle is to its lateral-grip limit and which axle limits
first (front = understeer, rear = oversteer). It responds to the anti-roll-bar
balance (``k_roll_front``/``k_roll_rear``) exactly as Sonnino et al. (2026)
describe — see docs/research/RSD_Sonnino2026_roll_stiffness_synthesis.md.

Pure post-processing: reads the solved lateral-accel/speed channels plus the
vehicle scalars, never touches the two-pass solver, so it cannot change a lap
time. It mirrors the solver's ``_axle_grip`` load-transfer and load-sensitivity
formulas so the diagnostic matches the physics the lap was solved with.

Physics per cornering point:

    RSD        = k_roll_f / (k_roll_f + k_roll_r)                 (front roll share)
    F_aero     = -0.5 * rho * Cl * A * v^2                        (downforce, Cl<0)
    Fz_f       = m*g*lr/L + F_aero*aero_balance                   (static front axle load)
    Fz_r       = m*g*lf/L + F_aero*(1-aero_balance)
    dFz_f      = (m*|a_y|*h_cg / t_f) * RSD                       (Eq 3, front transfer)
    dFz_r      = (m*|a_y|*h_cg / t_r) * (1-RSD)
    ls_i       = 1 - S_LOAD * min(dFz_i / (Fz_i/2), 0.95)         (load sensitivity)
    grip_i     = mu * ls_i * Fz_i                                 (axle lateral capacity)
    demand_f   = m*|a_y|*lr/L,  demand_r = m*|a_y|*lf/L           (steady moment balance)
    util_i     = demand_i / grip_i                               (0..~1, 1 = at the limit)
    balance    = util_f - util_r                                 (>0 understeer, <0 oversteer)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

_G = 9.81
_RHO_AIR = 1.225
_S_LOAD = 0.12          # tyre load sensitivity (matches solver _S_LOAD)
_CORNER_MIN_AY = 1.0    # [m/s²] below this the point is treated as straight-line


@dataclass(frozen=True)
class BalanceGeometry:
    """Vehicle scalars for the handling-balance diagnostic (SI unless noted)."""
    mu: float
    lf: float
    lr: float
    h_cg: float
    mass: float
    cl: float
    a_front: float
    k_roll_front: float
    k_roll_rear: float
    track_front: float
    track_rear: float
    aero_balance: float     # front share of aero vertical load (0-1)


@dataclass(frozen=True)
class BalanceChannels:
    """Per-point handling-balance channels (same length as the input trace)."""
    front_utilisation: np.ndarray   # demand/grip front, 0 off-corner
    rear_utilisation: np.ndarray    # demand/grip rear, 0 off-corner
    balance: np.ndarray             # util_f - util_r (>0 understeer, <0 oversteer)
    understeer: np.ndarray          # True where the front axle limits (balance>0)


def geometry_from_params(params: dict) -> BalanceGeometry:
    """Build a :class:`BalanceGeometry` from a flat solver parameter dict."""
    return BalanceGeometry(
        mu=float(params["mu"]),
        lf=float(params["lf"]),
        lr=float(params["lr"]),
        h_cg=float(params["h_cg"]),
        mass=float(params["m"]),
        cl=float(params["Cl"]),
        a_front=float(params["A_front"]),
        k_roll_front=float(params["k_roll_front"]),
        k_roll_rear=float(params["k_roll_rear"]),
        track_front=float(params["track_width_front"]),
        track_rear=float(params["track_width_rear"]),
        aero_balance=float(params.get("aero_balance", 0.5)),
    )


def roll_stiffness_distribution(geom: BalanceGeometry) -> float:
    """Front roll-stiffness share RSD = k_roll_f / (k_roll_f + k_roll_r)."""
    total = geom.k_roll_front + geom.k_roll_rear
    return geom.k_roll_front / total if total > 0.0 else 0.5


def handling_balance(
    a_lat_ms2: np.ndarray,
    v_ms: np.ndarray,
    geom: BalanceGeometry,
) -> BalanceChannels:
    """Per-axle grip utilisation and under/oversteer balance along a lap.

    Args:
        a_lat_ms2: Lateral acceleration trace [m/s²]; sign ignored.
        v_ms: Speed trace [m/s].
        geom: Vehicle scalars.

    Returns:
        BalanceChannels. Straight-line points (|a_y| < _CORNER_MIN_AY) are 0.
    """
    a_lat = np.abs(np.asarray(a_lat_ms2, dtype=float))
    v = np.asarray(v_ms, dtype=float)
    if a_lat.shape != v.shape:
        raise ValueError("a_lat_ms2 and v_ms must have the same shape.")

    wheelbase = geom.lf + geom.lr
    rsd = roll_stiffness_distribution(geom)

    f_aero = -0.5 * _RHO_AIR * geom.cl * geom.a_front * v ** 2
    fz_f = geom.mass * _G * geom.lr / wheelbase + f_aero * geom.aero_balance
    fz_r = geom.mass * _G * geom.lf / wheelbase + f_aero * (1.0 - geom.aero_balance)
    fz_f = np.maximum(fz_f, 1.0)
    fz_r = np.maximum(fz_r, 1.0)

    lat_moment = geom.mass * a_lat * geom.h_cg
    dfz_f = lat_moment / geom.track_front * rsd
    dfz_r = lat_moment / geom.track_rear * (1.0 - rsd)

    ls_f = 1.0 - _S_LOAD * np.minimum(dfz_f / (fz_f / 2.0), 0.95)
    ls_r = 1.0 - _S_LOAD * np.minimum(dfz_r / (fz_r / 2.0), 0.95)

    grip_f = geom.mu * ls_f * fz_f
    grip_r = geom.mu * ls_r * fz_r

    demand_f = geom.mass * a_lat * geom.lr / wheelbase
    demand_r = geom.mass * a_lat * geom.lf / wheelbase

    cornering = a_lat >= _CORNER_MIN_AY
    util_f = np.where(cornering, demand_f / np.maximum(grip_f, 1.0), 0.0)
    util_r = np.where(cornering, demand_r / np.maximum(grip_r, 1.0), 0.0)
    balance = util_f - util_r

    return BalanceChannels(
        front_utilisation=util_f,
        rear_utilisation=util_r,
        balance=balance,
        understeer=(balance > 0.0) & cornering,
    )


def balance_metrics(channels: BalanceChannels) -> dict[str, float]:
    """Aggregate handling-balance KPIs over the cornering part of a lap.

    Returns:
        Dict with mean signed balance (>0 understeer), the fraction of cornering
        points that understeer, and peak front/rear utilisation.
    """
    cornering = (channels.front_utilisation > 0.0) | (channels.rear_utilisation > 0.0)
    n = int(np.count_nonzero(cornering))
    if n == 0:
        return {"mean_balance": 0.0, "understeer_fraction": 0.0,
                "peak_front_utilisation": 0.0, "peak_rear_utilisation": 0.0}
    return {
        "mean_balance": float(np.mean(channels.balance[cornering])),
        "understeer_fraction": float(np.count_nonzero(channels.understeer)) / n,
        "peak_front_utilisation": float(np.max(channels.front_utilisation)),
        "peak_rear_utilisation": float(np.max(channels.rear_utilisation)),
    }
