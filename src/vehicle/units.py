"""
Unit conversion helpers for vehicle parameters.

Single source of truth for unit conversions used across the UI and
vehicle modules. UI widgets collect values in field-friendly units
(e.g. tyre pressure in psi) and convert exactly once at the
widget -> dataclass boundary using these helpers.

Author: Lap Time Simulator Team
"""

PSI_PER_BAR: float = 14.5038  # 1 bar = 14.5038 psi


def psi_to_bar(pressure_psi: float) -> float:
    """Convert pressure from psi to bar.

    Args:
        pressure_psi: Pressure [psi].

    Returns:
        Pressure [bar].
    """
    return pressure_psi / PSI_PER_BAR


def bar_to_psi(pressure_bar: float) -> float:
    """Convert pressure from bar to psi.

    Args:
        pressure_bar: Pressure [bar].

    Returns:
        Pressure [psi].
    """
    return pressure_bar * PSI_PER_BAR
