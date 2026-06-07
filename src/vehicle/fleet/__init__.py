"""
Fleet registry for all available vehicle models.

Provides a unified interface to access any supported vehicle by ID,
enabling multi-vehicle simulation and comparison workflows.

Author: Lap Time Simulator Team
Date: 2026-03-10
"""

import json
from pathlib import Path
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

# Dynamic loading of JSON models (Copa Truck presets)
_JSON_MODELS_CACHE: Dict[str, VehicleParams] = {}


def _load_json_models() -> None:
    if not _JSON_MODELS_CACHE:
        json_path = Path(__file__).parent.parent.parent.parent / "data" / "vehicle_models.json"
        if json_path.exists():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for key, val in data.items():
                    vp = VehicleParams.from_solver_dict(val)
                    if "name" in val:
                        vp.name = val["name"]
                    _JSON_MODELS_CACHE[key] = vp
            except Exception:
                pass


def get_vehicle_by_id(vehicle_id: str) -> VehicleParams:
    """
    Retrieve a vehicle instance from the fleet registry.

    Args:
        vehicle_id: Registry key (e.g., 'porsche_991_1', 'volkswagen_31320').

    Returns:
        VehicleParams instance with default setup applied.

    Raises:
        KeyError: If vehicle_id is not registered.
    """
    if vehicle_id in _FLEET_REGISTRY:
        return _FLEET_REGISTRY[vehicle_id]()
    
    _load_json_models()
    if vehicle_id in _JSON_MODELS_CACHE:
        # Return a copy to avoid mutation contamination
        return VehicleParams.from_dict(_JSON_MODELS_CACHE[vehicle_id].to_dict())

    available = list(_FLEET_REGISTRY.keys()) + list(_JSON_MODELS_CACHE.keys())
    raise KeyError(
        f"Vehicle '{vehicle_id}' not found. Available: {available}")


def list_vehicles() -> Dict[str, str]:
    """
    List all registered vehicles with their display names.

    Returns:
        Dict mapping vehicle_id -> vehicle name string.
    """
    _load_json_models()
    vehicles = {vid: get_vehicle_by_id(vid).name for vid in _FLEET_REGISTRY}
    for vid, vp in _JSON_MODELS_CACHE.items():
        vehicles[vid] = vp.name
    return vehicles


def list_vehicle_ids() -> list:
    """Return a list of all registered vehicle IDs."""
    _load_json_models()
    return list(_FLEET_REGISTRY.keys()) + list(_JSON_MODELS_CACHE.keys())


__all__ = [
    "get_vehicle_by_id",
    "list_vehicles",
    "list_vehicle_ids",
    "porsche_gt3_cup_991_1",
    "porsche_gt3_cup_991_2",
    "porsche_gt3_cup_992_1",
]

