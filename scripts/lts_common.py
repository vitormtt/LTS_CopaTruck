"""
Shared utilities for the calibration and sensitivity CLI scripts.

Centralises project-path bootstrapping, solver-logging suppression,
circuit loading and single-lap simulation so that both
``sensitivity_analysis.py`` and ``calibrate_vehicle.py`` use the exact
same simulation pipeline (``run_simulation`` + default ``VehicleSetup``).

Author: Lap Time Simulator Team
Date: 2026-06-11
"""

from __future__ import annotations

import copy
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Imports below depend on PROJECT_ROOT being on sys.path.
from src.simulation.lap_time_solver import (  # noqa: E402
    SimulationResult,
    run_simulation,
)
from src.simulation.simulation_modes import SimulationConfig  # noqa: E402
from src.tracks.hdf5 import CircuitHDF5Reader  # noqa: E402
from src.vehicle.fleet import get_vehicle_by_id  # noqa: E402
from src.vehicle.parameters import VehicleParams  # noqa: E402
from src.vehicle.setup import VehicleSetup, get_default_setup  # noqa: E402

TRACKS_DIR: Path = PROJECT_ROOT / "tracks"
RESULTS_DIR: Path = PROJECT_ROOT / "src" / "results"
DATA_DIR: Path = PROJECT_ROOT / "data"


def silence_solver_logging() -> None:
    """Disable all logging output so batch runs do not flood stdout."""
    logging.disable(logging.CRITICAL)


def load_circuit(track_id: str) -> Any:
    """Load a circuit from ``tracks/<track_id>.hdf5``.

    Args:
        track_id: Track file stem (e.g. ``"cascavel"``, ``"interlagos"``).

    Returns:
        CircuitData instance read from the HDF5 file.

    Raises:
        FileNotFoundError: If the HDF5 file does not exist; the message
            lists the available track files.
    """
    path = TRACKS_DIR / f"{track_id}.hdf5"
    if not path.exists():
        available = sorted(p.stem for p in TRACKS_DIR.glob("*.hdf5"))
        raise FileNotFoundError(
            f"Track '{track_id}' not found at {path}. Available: {available}"
        )
    circuit, _meta = CircuitHDF5Reader(str(path)).read_circuit()
    return circuit


def load_vehicle(vehicle_id: str) -> VehicleParams:
    """Return a fresh ``VehicleParams`` instance from the fleet registry.

    Args:
        vehicle_id: Fleet registry key (e.g. ``"volkswagen_31320"``).

    Returns:
        Independent VehicleParams copy safe for in-place mutation.
    """
    return get_vehicle_by_id(vehicle_id)


def simulate_lap(
    vehicle_params: VehicleParams,
    circuit: Any,
    track_id: str = "interlagos",
    setup: Optional[VehicleSetup] = None,
) -> SimulationResult:
    """Run a single qualifying lap and return the full SimulationResult.

    The two-pass GGV solver itself is never modified here — this is a
    thin, read-only wrapper around ``run_simulation``.

    Args:
        vehicle_params: Vehicle to simulate (deep-copied internally so the
            caller's instance is never mutated by the setup application).
        circuit: CircuitData track geometry.
        track_id: Track identifier (informational, used by the config).
        setup: Optional VehicleSetup; defaults to ``get_default_setup()``.

    Returns:
        SimulationResult with ``lap_time``, ``distance``, ``v_kmh``, etc.
    """
    config = SimulationConfig.qualifying(track_id=track_id)
    config.setup = setup if setup is not None else get_default_setup()
    return run_simulation(
        config=config,
        vehicle_params=copy.deepcopy(vehicle_params),
        circuit=circuit,
        save_csv=False,
    )


@dataclass
class ContinuousArbSetup(VehicleSetup):
    """VehicleSetup variant with continuous ARB stiffness overrides.

    ``apply_setup`` always overwrites ``k_roll_front``/``k_roll_rear`` from
    the discrete ARB position lookup tables, so perturbing the
    ``VehicleParams`` roll-stiffness fields directly has no effect on the
    solver. This subclass exposes continuous overrides for the stiffness
    properties, enabling OAT sensitivity on the roll-stiffness split
    without touching the solver or the setup module.

    Attributes:
        k_front_override: Front ARB torsional stiffness [Nm/rad] or None.
        k_rear_override: Rear ARB torsional stiffness [Nm/rad] or None.
    """

    k_front_override: Optional[float] = None
    k_rear_override: Optional[float] = None

    @property
    def arb_front_stiffness(self) -> float:
        """Front ARB stiffness [Nm/rad] — override or position lookup."""
        if self.k_front_override is not None:
            return self.k_front_override
        return VehicleSetup.arb_front_stiffness.fget(self)  # type: ignore[attr-defined]

    @property
    def arb_rear_stiffness(self) -> float:
        """Rear ARB stiffness [Nm/rad] — override or position lookup."""
        if self.k_rear_override is not None:
            return self.k_rear_override
        return VehicleSetup.arb_rear_stiffness.fget(self)  # type: ignore[attr-defined]
