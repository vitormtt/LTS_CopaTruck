"""Driver-facing brake-lockup and handling-balance report.

Bundles the two derived diagnostic channels (:mod:`brake_lockup` and
:mod:`handling_balance`) into a single object computed straight from a solver
result dict, so the Streamlit results page and the PDF exporter share one pure,
tested code path instead of duplicating the wiring.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .brake_lockup import (
    LockupChannels,
    geometry_from_params as lockup_geometry_from_params,
    lockup_margins,
    lockup_metrics,
)
from .handling_balance import (
    BalanceChannels,
    geometry_from_params as balance_geometry_from_params,
    handling_balance,
    balance_metrics,
)

_REQUIRED_KEYS = ("v_profile", "a_long", "a_lat")


@dataclass(frozen=True)
class DriverReport:
    """Per-point channels plus aggregate KPIs for one lap."""

    lockup: LockupChannels
    balance: BalanceChannels
    lockup_kpis: dict[str, float]
    balance_kpis: dict[str, float]


def driver_report_from_result(result: dict, params: dict) -> DriverReport:
    """Build the driver diagnostic report from a solver result dict.

    Args:
        result: Solver output with ``v_profile`` [m/s], ``a_long`` [m/s²,
            negative under braking] and ``a_lat`` [m/s², sign ignored].
        params: Flat vehicle-parameter dict (as ``VehicleParams.to_solver_dict``),
            consumed by the two channel geometries.

    Returns:
        A :class:`DriverReport` with both channel traces and their KPIs.

    Raises:
        KeyError: If ``result`` is missing a required kinematic channel.
    """
    missing = [k for k in _REQUIRED_KEYS if k not in result]
    if missing:
        raise KeyError(f"result is missing required channels: {missing}")

    v_ms = np.asarray(result["v_profile"], dtype=float)
    a_long = np.asarray(result["a_long"], dtype=float)
    a_lat = np.asarray(result["a_lat"], dtype=float)

    lockup = lockup_margins(v_ms, a_long, lockup_geometry_from_params(params))
    balance = handling_balance(a_lat, v_ms, balance_geometry_from_params(params))

    return DriverReport(
        lockup=lockup,
        balance=balance,
        lockup_kpis=lockup_metrics(lockup),
        balance_kpis=balance_metrics(balance),
    )
