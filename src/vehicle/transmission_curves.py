"""Transmission design curves (speed per gear, tractive force vs speed).

Design-view companion to the transmission section of the vehicle-parameters
page: from the gear set, final drive, wheel radius and the engine torque
curve it builds the plots an engineer inspects to validate the gearing —
speed coverage per gear and the tractive-force sawtooth against the
resistance curve (drag + rolling).

Pure module: no Streamlit, no solver import.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

import numpy as np

_RHO_AIR = 1.225           # air density [kg/m³]
_G = 9.81                  # gravity [m/s²]
_ROLLING_COEFF = 0.008     # truck racing radial rolling resistance [-]
_N_POINTS = 120
_MIN_SPEED_KMH = 5.0       # avoid the v=0 singularity in the F(v) sweep


@dataclass(frozen=True)
class GearCurve:
    """Per-gear traces over the engine speed range."""

    gear: int                   # 1-based gear number
    rpm: np.ndarray             # engine speed [rpm]
    speed_kmh: np.ndarray       # road speed [km/h]
    tractive_force_n: np.ndarray  # force at the contact patch [N]


def speed_kmh_at_rpm(rpm: np.ndarray, ratio: float, final_drive: float,
                     wheel_radius_m: float) -> np.ndarray:
    """Road speed for an engine speed in one gear.

    Args:
        rpm: Engine speed [rpm].
        ratio: Gearbox ratio of the selected gear [-].
        final_drive: Final drive (differential) ratio [-].
        wheel_radius_m: Rolling radius [m].

    Returns:
        Road speed [km/h].
    """
    wheel_rad_s = np.asarray(rpm, dtype=float) * 2.0 * np.pi / 60.0 \
        / (ratio * final_drive)
    return wheel_rad_s * wheel_radius_m * 3.6


def gear_curves(
    gear_ratios: Sequence[float],
    final_drive: float,
    wheel_radius_m: float,
    torque_curve_rpm: Sequence[float],
    torque_curve_nm: Sequence[float],
    max_torque_nm: float,
    rpm_idle: float,
    rpm_max: float,
    driveline_efficiency: float = 1.0,
) -> List[GearCurve]:
    """Speed and tractive-force traces for every gear.

    Torque comes from the engine curve when present, else flat
    ``max_torque_nm`` (same fallback the solver uses).

    Args:
        gear_ratios: Gearbox ratios, 1st..top.
        final_drive: Final drive ratio [-].
        wheel_radius_m: Rolling radius [m].
        torque_curve_rpm: Engine curve abscissa [rpm] (may be empty).
        torque_curve_nm: Engine curve torque [Nm] (may be empty).
        max_torque_nm: Flat-torque fallback [Nm].
        rpm_idle: Lower engine speed bound [rpm].
        rpm_max: Upper engine speed bound [rpm].
        driveline_efficiency: Driveline efficiency [-].

    Returns:
        One GearCurve per gear.

    Raises:
        ValueError: If the rpm bounds are not increasing.
    """
    if rpm_max <= rpm_idle:
        raise ValueError("rpm_max must exceed rpm_idle.")

    rpm = np.linspace(rpm_idle, rpm_max, _N_POINTS)
    if len(torque_curve_rpm) >= 2 and len(torque_curve_rpm) == len(torque_curve_nm):
        torque = np.interp(rpm, torque_curve_rpm, torque_curve_nm)
    else:
        torque = np.full_like(rpm, max_torque_nm)

    curves: List[GearCurve] = []
    for i, ratio in enumerate(gear_ratios, start=1):
        speed = speed_kmh_at_rpm(rpm, ratio, final_drive, wheel_radius_m)
        force = torque * ratio * final_drive * driveline_efficiency \
            / wheel_radius_m
        curves.append(GearCurve(gear=i, rpm=rpm, speed_kmh=speed,
                                tractive_force_n=force))
    return curves


def resistance_curve(
    mass_kg: float,
    cx: float,
    frontal_area_m2: float,
    speed_max_kmh: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Road-load resistance (aero drag + rolling) over a speed sweep.

    Args:
        mass_kg: Vehicle mass [kg].
        cx: Drag coefficient [-].
        frontal_area_m2: Frontal area [m²].
        speed_max_kmh: Upper bound of the sweep [km/h].

    Returns:
        (speed_kmh, resistance_n) arrays.
    """
    speed_kmh = np.linspace(_MIN_SPEED_KMH, speed_max_kmh, _N_POINTS)
    v_ms = speed_kmh / 3.6
    drag = 0.5 * _RHO_AIR * cx * frontal_area_m2 * v_ms ** 2
    rolling = np.full_like(v_ms, _ROLLING_COEFF * mass_kg * _G)
    return speed_kmh, drag + rolling
