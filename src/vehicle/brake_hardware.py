"""
Brake capacity from hardware — the Limpert brake-torque chain.

Derives the maximum brake force at the tyre contact patch from physical
brake components (caliper pistons, line pressure, pad friction, disc
effective radius, wheel radius) instead of a hand-tuned ``max_brake_force``
number. The tyre-grip limit is applied separately by the solver
(``_bias_limited_decel``); this module only sizes the brake *system*
ceiling.

Chain per axle (Limpert 1999, Brake Design and Safety, ch. 2 & 7):

    clamp_force   = P_line * A_piston * n_pistons          (one caliper)
    brake_torque  = 2 * mu_pad * clamp_force * R_disc_eff   (two pad faces)
    force_at_tyre = brake_torque / R_wheel * wheels_per_axle

Piston/pressure inputs describe ONE caliper; an axle carries one caliper
per wheel, so the axle force scales by ``wheels_per_axle`` (2 on a truck).
Total vehicle brake force = front axle + rear axle.

All values SI unless the field name says otherwise (pressure in bar at the
UI boundary, converted here).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

_BAR_TO_PA = 1e5
_PAD_FACES = 2  # a disc is clamped by two pads


@dataclass(frozen=True)
class BrakeHardware:
    """Physical brake hardware of a single axle.

    Attributes:
        n_pistons: Number of pistons in one caliper.
        piston_diameter_m: Caliper piston diameter [m].
        line_pressure_bar: Peak hydraulic line pressure [bar].
        pad_friction: Pad-disc friction coefficient [-].
        disc_effective_radius_m: Mean radius where pads act on the disc [m].
        wheel_radius_m: Rolling wheel radius [m].
        wheels_per_axle: Braked wheels (one caliper each) on the axle.
    """
    n_pistons: int
    piston_diameter_m: float
    line_pressure_bar: float
    pad_friction: float
    disc_effective_radius_m: float
    wheel_radius_m: float
    wheels_per_axle: int = 2


def axle_brake_force(hw: BrakeHardware) -> float:
    """Maximum longitudinal brake force one axle can put at the contact patch.

    Args:
        hw: Axle brake hardware.

    Returns:
        Brake force at the tyre [N].

    Raises:
        ValueError: If ``wheel_radius_m`` is not positive.
    """
    if hw.wheel_radius_m <= 0.0:
        raise ValueError("wheel_radius_m must be positive.")

    piston_area = math.pi * (hw.piston_diameter_m / 2.0) ** 2
    clamp = hw.line_pressure_bar * _BAR_TO_PA * piston_area * hw.n_pistons
    torque = _PAD_FACES * hw.pad_friction * clamp * hw.disc_effective_radius_m
    return torque / hw.wheel_radius_m * hw.wheels_per_axle


def brake_force_from_hardware(
    front: BrakeHardware,
    rear: BrakeHardware,
) -> float:
    """Total vehicle brake force from front and rear axle hardware.

    Args:
        front: Front axle brake hardware.
        rear: Rear axle brake hardware.

    Returns:
        Total brake force at the tyres [N] (front + rear).
    """
    return axle_brake_force(front) + axle_brake_force(rear)
