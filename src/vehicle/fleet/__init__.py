"""
Fleet registry for all available vehicle models.

Provides a unified interface to access any supported vehicle by ID,
enabling multi-vehicle simulation and comparison workflows.

Author: Lap Time Simulator Team
Date: 2026-03-10
"""

from typing import Dict, Callable
from ..parameters import VehicleParams

from .porsche_gt3_991_1 import porsche_gt3_cup_991_1
from .porsche_gt3_991_2 import porsche_gt3_cup_991_2
from .porsche_gt3_992_1 import porsche_gt3_cup_992_1


# Registry: vehicle_id -> factory function
_FLEET_REGISTRY: Dict[str, Callable[[], VehicleParams]] = {
    "porsche_991_1": porsche_gt3_cup_991_1,
    "porsche_991_2": porsche_gt3_cup_991_2,
    "porsche_992_1": porsche_gt3_cup_992_1,
}


def get_vehicle_by_id(vehicle_id: str) -> VehicleParams:
    """
    Retrieve a vehicle instance from the fleet registry.

    Args:
        vehicle_id: Registry key (e.g., 'porsche_991_1').

    Returns:
        VehicleParams instance with default setup applied.

    Raises:
        KeyError: If vehicle_id is not registered.
    """
    if vehicle_id not in _FLEET_REGISTRY:
        available = list(_FLEET_REGISTRY.keys())
        raise KeyError(
            f"Vehicle '{vehicle_id}' not found. Available: {available}")
    return _FLEET_REGISTRY[vehicle_id]()


def list_vehicles() -> Dict[str, str]:
    """
    List all registered vehicles with their display names.

    Returns:
        Dict mapping vehicle_id -> vehicle name string.
    """
    return {vid: get_vehicle_by_id(vid).name for vid in _FLEET_REGISTRY}


def list_vehicle_ids() -> list:
    """Return a list of all registered vehicle IDs."""
    return list(_FLEET_REGISTRY.keys())


__all__ = [
    "get_vehicle_by_id",
    "list_vehicles",
    "list_vehicle_ids",
    "porsche_gt3_cup_991_1",
    "porsche_gt3_cup_991_2",
    "porsche_gt3_cup_992_1",
]
