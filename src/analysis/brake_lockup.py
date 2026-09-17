"""
Brake lockup analysis — per-axle wheel-lock margin for driver training.

Copa Truck runs without ABS, so a driver who over-brakes locks a wheel and
loses time (and stability). This module derives, from an already-solved lap,
how close each axle is to locking at every point — a risk channel that shows
where lockup is most likely and how the brake bias splits the load.

It is pure post-processing: it reads the solved deceleration/speed channels
plus the vehicle scalars and never touches the two-pass solver, so it cannot
change a lap time (golden rule #2).

Physics (Limpert 1999, Brake Design and Safety, ch. 7 — mirrors the solver's
``_bias_limited_decel``). Under deceleration ``a`` the longitudinal load
transfer shifts ``m*a*h_cg/L`` from the rear axle to the front. With a front
brake-bias fraction ``b`` the deceleration at which each axle first locks is::

    a_front_lock = mu*g_eff*(lr/L) / (b - mu*h_cg/L)      (if b > mu*h_cg/L)
    a_rear_lock  = mu*g_eff*(lf/L) / ((1-b) + mu*h_cg/L)

where ``g_eff = F_normal/m`` folds in aerodynamic downforce. The per-axle
lockup margin is ``|decel| / a_axle_lock``: 1.0 means the axle is on the
verge of locking, the axle nearer 1.0 is the one that locks first. Slip ratio
is estimated as ``peak_slip * margin`` (linear up to the peak-slip point,
KB §10: ``sx = (omega*Re - vx)/vx``).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

_G = 9.81           # [m/s²]
_RHO_AIR = 1.225    # [kg/m³]
_PEAK_SLIP = 0.15   # slip ratio at peak longitudinal force (matches solver)


@dataclass(frozen=True)
class LockupGeometry:
    """Vehicle scalars needed to size axle lockup (SI unless noted)."""
    mu: float               # tyre-road friction coefficient [-]
    brake_balance_pct: float  # front brake bias [%]
    lf: float               # CG-to-front-axle distance [m]
    lr: float               # CG-to-rear-axle distance [m]
    h_cg: float             # CG height [m]
    mass: float             # vehicle mass [kg]
    cl: float               # lift coefficient (negative = downforce) [-]
    a_front: float          # frontal area [m²]


@dataclass(frozen=True)
class LockupChannels:
    """Per-point lockup risk channels (same length as the input trace)."""
    front_margin: np.ndarray   # |decel| / a_front_lock, 0.0 when not braking
    rear_margin: np.ndarray    # |decel| / a_rear_lock, 0.0 when not braking
    front_limited: np.ndarray  # True where the front axle locks first
    slip_estimate: np.ndarray  # peak_slip * limiting-axle margin


def axle_lock_decels(
    mu: float,
    g_eff: float,
    bias_frac: float,
    lf: float,
    lr: float,
    h_cg: float,
) -> tuple[float, float]:
    """Deceleration at which the front and rear axle first lock [m/s²].

    Args:
        mu: Tyre-road friction coefficient.
        g_eff: Effective gravity F_normal/m (folds in downforce) [m/s²].
        bias_frac: Front brake bias fraction (0-1).
        lf: CG-to-front-axle distance [m].
        lr: CG-to-rear-axle distance [m].
        h_cg: CG height [m].

    Returns:
        (a_front_lock, a_rear_lock) [m/s²]. a_front_lock is ``inf`` when load
        transfer keeps the front axle below lock-up at any deceleration.
    """
    wheelbase = lf + lr
    mu_h_over_l = mu * h_cg / wheelbase

    a_rear = mu * g_eff * (lf / wheelbase) / ((1.0 - bias_frac) + mu_h_over_l)
    if bias_frac > mu_h_over_l:
        a_front = mu * g_eff * (lr / wheelbase) / (bias_frac - mu_h_over_l)
    else:
        a_front = float("inf")
    return a_front, a_rear


def lockup_margins(
    v_ms: np.ndarray,
    a_long_ms2: np.ndarray,
    geom: LockupGeometry,
) -> LockupChannels:
    """Per-axle lockup margin along a solved lap.

    Args:
        v_ms: Speed trace [m/s].
        a_long_ms2: Longitudinal acceleration trace [m/s²]; negative = braking.
        geom: Vehicle scalars.

    Returns:
        LockupChannels with per-point front/rear margins, limiting-axle flag,
        and a slip-ratio estimate. Non-braking points (a_long >= 0) are 0.0.
    """
    v = np.asarray(v_ms, dtype=float)
    a_long = np.asarray(a_long_ms2, dtype=float)
    if v.shape != a_long.shape:
        raise ValueError("v_ms and a_long_ms2 must have the same shape.")

    bias_frac = geom.brake_balance_pct / 100.0
    # Effective gravity per point: g minus downforce/mass (cl < 0 = downforce).
    f_normal = geom.mass * _G - 0.5 * _RHO_AIR * geom.cl * geom.a_front * v ** 2
    g_eff = np.maximum(f_normal, 0.0) / geom.mass

    decel = np.where(a_long < 0.0, -a_long, 0.0)  # braking magnitude

    front_margin = np.zeros_like(v)
    rear_margin = np.zeros_like(v)
    for i in range(len(v)):
        if decel[i] <= 0.0:
            continue
        a_front, a_rear = axle_lock_decels(
            geom.mu, float(g_eff[i]), bias_frac, geom.lf, geom.lr, geom.h_cg
        )
        front_margin[i] = decel[i] / a_front if np.isfinite(a_front) else 0.0
        rear_margin[i] = decel[i] / a_rear

    front_limited = front_margin >= rear_margin
    limiting_margin = np.where(front_limited, front_margin, rear_margin)
    slip_estimate = _PEAK_SLIP * np.clip(limiting_margin, 0.0, 1.0)

    return LockupChannels(
        front_margin=front_margin,
        rear_margin=rear_margin,
        front_limited=front_limited & (decel > 0.0),
        slip_estimate=slip_estimate,
    )


def geometry_from_params(params: dict) -> LockupGeometry:
    """Build a :class:`LockupGeometry` from a flat solver parameter dict.

    Args:
        params: Flat solver dict (``VehicleParams.to_solver_dict()`` output).

    Returns:
        LockupGeometry with the scalars the lockup model needs.
    """
    return LockupGeometry(
        mu=float(params["mu"]),
        brake_balance_pct=float(params["brake_balance"]),
        lf=float(params["lf"]),
        lr=float(params["lr"]),
        h_cg=float(params["h_cg"]),
        mass=float(params["m"]),
        cl=float(params["Cl"]),
        a_front=float(params["A_front"]),
    )


def lockup_metrics(channels: LockupChannels, near_lock: float = 0.90) -> dict[str, float]:
    """Aggregate lockup KPIs for a lap.

    Args:
        channels: Output of :func:`lockup_margins`.
        near_lock: Margin threshold counted as "near lockup".

    Returns:
        Dict with peak front/rear margins and the fraction of the braking
        trace spent within ``near_lock`` of a wheel lock.
    """
    braking = (channels.front_margin > 0.0) | (channels.rear_margin > 0.0)
    n_braking = int(np.count_nonzero(braking))
    limiting = np.maximum(channels.front_margin, channels.rear_margin)
    near = float(np.count_nonzero(limiting[braking] >= near_lock)) / n_braking \
        if n_braking else 0.0
    return {
        "peak_front_margin": float(np.max(channels.front_margin, initial=0.0)),
        "peak_rear_margin": float(np.max(channels.rear_margin, initial=0.0)),
        "near_lockup_fraction": near,
    }
