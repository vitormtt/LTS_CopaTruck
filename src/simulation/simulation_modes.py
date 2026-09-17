"""
Simulation modes module for lap time simulator.

Defines the SimulationMode enum and SimulationConfig dataclass that
control how the GGV solver is initialised and executed for each
simulation scenario.

References
----------
- Segers, J. (2014). Analysis Techniques for Racecar Data Acquisition,
  2nd Ed. SAE International.
- Brayshaw, D.L. & Harrison, M.F. (2005). A quasi steady state approach
  to race car lap simulation. Proc. IMechE, Part D.
- Pi Toolbox Apostila de Treinamento — Porsche Carrera Cup Brasil (2014).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional

from ..vehicle.setup import VehicleSetup, get_default_setup


class SimulationMode(Enum):
    """
    Enumeration of available simulation scenarios.

    QUALIFYING       : single fastest lap from equilibrium speed.
    FLYING_LAP       : lap from a prescribed constant entry speed.
    STANDING_START   : lap from standstill with launch sequence.
    ROLLING_START    : alias for FLYING_LAP (backward compatibility).
    """
    QUALIFYING        = auto()
    FLYING_LAP        = auto()
    STANDING_START    = auto()
    ROLLING_START     = auto()


@dataclass
class DriverInputChannels:
    """
    Telemetry channels for driver input monitoring and optimization.

    All channels are time-series arrays aligned with the simulation time vector.
    """
    throttle: List[float] = field(default_factory=list)
    brake: List[float] = field(default_factory=list)
    steering_angle: List[float] = field(default_factory=list)
    gear: List[int] = field(default_factory=list)
    shift_events: List[float] = field(default_factory=list)
    braking_points: List[float] = field(default_factory=list)
    long_g: List[float] = field(default_factory=list)
    lat_g: List[float] = field(default_factory=list)
    speed: List[float] = field(default_factory=list)
    rpm: List[float] = field(default_factory=list)


@dataclass
class SimulationConfig:
    """
    Full configuration for a single simulation run.

    Parameters
    ----------
    mode : SimulationMode
    setup : VehicleSetup
    n_laps : int
    v_entry_kmh : float
        Initial speed for FLYING_LAP [km/h].
    launch_rpm : float
        Clutch-drop RPM for STANDING_START [rev/min].
    track_temperature_c : float
        Track surface temperature [degC].
    tyre_compound : str
    export_driver_inputs : bool
    notes : str
    """
    mode: SimulationMode = SimulationMode.QUALIFYING
    setup: VehicleSetup = field(default_factory=get_default_setup)

    n_laps: int = 1
    track_temperature_c: float = 35.0
    tyre_compound: str = "slick_dry"
    export_driver_inputs: bool = True
    # Drive the minimum-curvature racing line instead of the centerline.
    # Default True since 2026-07-10 (operator directive): a hot lap never
    # follows the centerline. False = explicit centerline-baseline debug.
    use_racing_line: bool = True
    # Start the qualifying lap from the flying-lap periodic speed (v0 = exit
    # speed of the closed lap) instead of the cold ~36 km/h launch. Default
    # True since 2026-07-10: a qualifying hot lap IS a flying lap by
    # definition — the old v0=10 m/s launch leaked ~4.5 s into the lap and
    # the mu fudge was co-calibrated around it. Standing start unaffected.
    use_flying_lap_start: bool = True
    notes: str = ""

    v_entry_kmh: float = 100.0
    launch_rpm: float = 4500.0
    wheelspin_limit_slip: float = 0.25

    # Backward-compat aliases for HEAD-era attributes
    v0: float = 0.0
    lap_count: int = 1

    def __post_init__(self) -> None:
        """Sync lap_count -> n_laps; lap_count is deprecated, n_laps is authoritative."""
        if self.lap_count != self.n_laps:
            import warnings
            warnings.warn(
                f"SimulationConfig: lap_count={self.lap_count} ignored; "
                "use n_laps instead. lap_count will be removed in a future release.",
                DeprecationWarning,
                stacklevel=2,
            )
        self.lap_count = self.n_laps

    def is_qualifying(self) -> bool:
        return self.mode == SimulationMode.QUALIFYING

    def is_flying_lap(self) -> bool:
        return self.mode == SimulationMode.FLYING_LAP

    def is_standing_start(self) -> bool:
        return self.mode in (SimulationMode.STANDING_START,)

    def is_rolling_start(self) -> bool:
        return self.mode in (SimulationMode.ROLLING_START, SimulationMode.FLYING_LAP)

    def describe(self) -> str:
        """Human-readable summary string for logging."""
        base = (
            f"[{self.mode.name}] Setup='{self.setup.setup_name}' "
            f"Tyres={self.tyre_compound} T_track={self.track_temperature_c}\u00b0C"
        )
        if self.is_flying_lap():
            base += f" v_entry={self.v_entry_kmh:.1f} km/h"
        if self.is_standing_start():
            base += f" launch_rpm={self.launch_rpm:.0f} rpm"
        return base


    @classmethod
    def qualifying(cls, track_id: str = "interlagos", **kwargs) -> "SimulationConfig":
        """Shortcut constructor for qualifying simulation."""
        return cls(mode=SimulationMode.QUALIFYING, n_laps=1, lap_count=1, **kwargs)

    @classmethod
    def standing_start(cls, track_id: str = "interlagos", **kwargs) -> "SimulationConfig":
        """Shortcut constructor for standing start simulation."""
        return cls(mode=SimulationMode.STANDING_START, v0=0.0, lap_count=1, **kwargs)

    @classmethod
    def rolling_start(cls, v0_kmh: float, track_id: str = "interlagos", **kwargs) -> "SimulationConfig":
        """Shortcut constructor for rolling start at constant speed."""
        return cls(
            mode=SimulationMode.ROLLING_START,
            v0=v0_kmh / 3.6,
            v_entry_kmh=v0_kmh,
            lap_count=1,
            **kwargs,
        )


def get_default_config(
    mode: SimulationMode = SimulationMode.QUALIFYING,
    setup: Optional[VehicleSetup] = None,
) -> SimulationConfig:
    """Return a ready-to-use SimulationConfig with sensible defaults."""
    return SimulationConfig(
        mode=mode,
        setup=setup if setup is not None else get_default_setup(),
    )


# ---------------------------------------------------------------------------
# Driver input channel specification
# ---------------------------------------------------------------------------

DRIVER_INPUT_CHANNELS = [
    ("distance_m",   "m",    "Cumulative distance along track centreline"),
    ("lap_time_s",   "s",    "Cumulative lap time"),
    ("v_kmh",        "km/h", "Vehicle speed"),
    ("ax_long_g",    "g",    "Longitudinal acceleration (+ = accel, - = braking)"),
    ("ay_lat_g",     "g",    "Lateral acceleration (+ = left, - = right)"),
    ("throttle_pct", "%",    "Throttle pedal / drive torque request [0-100]"),
    ("brake_pct",    "%",    "Brake pedal pressure request [0-100]"),
    ("steering_deg", "deg",  "Steering wheel angle (+ = left)"),
    ("gear",         "-",    "Engaged gear number"),
    ("rpm",          "rpm",  "Engine rotational speed"),
]

DRIVER_INPUT_CHANNEL_NAMES: list = [ch[0] for ch in DRIVER_INPUT_CHANNELS]
