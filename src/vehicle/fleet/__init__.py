"""
Fleet registry for all available vehicle models.

Provides a unified interface to access any supported vehicle by ID,
enabling multi-vehicle simulation and comparison workflows.

Author: Lap Time Simulator Team
Date: 2026-06-10
"""

import json
import time
from pathlib import Path
from typing import Dict, Callable
from ..parameters import VehicleParams, validate_vehicle_params


# Registry: vehicle_id -> factory function (presets load from JSON below)
_FLEET_REGISTRY: Dict[str, Callable[[], VehicleParams]] = {}

# Dynamic loading of JSON models (Copa Truck presets)
_JSON_MODELS_CACHE: Dict[str, VehicleParams] = {}

# Auto-refresh: the cache is transparently reloaded from storage once it
# is older than the TTL, so edits made elsewhere (another session, psql,
# the seed script) show up in the UI without restarting the app.
_CACHE_TTL_S = 5.0
_cache_loaded_at = 0.0
_fleet_source = "none"  # "database" | "json" | "none" — for UI display


def fleet_source() -> str:
    """Where the current fleet cache was loaded from."""
    return _fleet_source


def _load_json_models() -> None:
    """Load and validate vehicle presets from database or local JSON file.

    Raises:
        ValueError: If any preset fails physical-consistency validation.
    """
    global _cache_loaded_at, _fleet_source
    if _JSON_MODELS_CACHE and (time.monotonic() - _cache_loaded_at) < _CACHE_TTL_S:
        return
    _JSON_MODELS_CACHE.clear()
    _cache_loaded_at = time.monotonic()

    # Try database first
    try:
        from src.database import db_manager
        db_vehicles = db_manager.list_vehicles()
        if db_vehicles:
            loaded: Dict[str, VehicleParams] = {}
            for key in db_vehicles.keys():
                val = db_manager.get_vehicle(key)
                if val:
                    vp = VehicleParams.from_solver_dict(val)
                    if "name" in val:
                        vp.name = val["name"]
                    errors = validate_vehicle_params(vp)
                    if not errors:
                        loaded[key] = vp
            if loaded:
                _JSON_MODELS_CACHE.update(loaded)
                _fleet_source = "database"
                return
    except Exception:
        # Fallback silently to local file database
        pass
    _fleet_source = "json"

    json_path = Path(__file__).parent.parent.parent.parent / "data" / "vehicle_models.json"
    if not json_path.exists():
        return
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        # Unreadable/corrupt preset file: behave as before (empty fleet).
        return

    loaded: Dict[str, VehicleParams] = {}
    for key, val in data.items():
        vp = VehicleParams.from_solver_dict(val)
        if "name" in val:
            vp.name = val["name"]
        errors = validate_vehicle_params(vp)
        if errors:
            raise ValueError(
                f"Invalid vehicle preset '{key}' in {json_path.name}: "
                + "; ".join(errors)
            )
        loaded[key] = vp
    # Only publish the cache once every preset validated cleanly, so a
    # failing preset cannot leave a partially populated fleet behind.
    _JSON_MODELS_CACHE.update(loaded)


def get_vehicle_by_id(vehicle_id: str) -> VehicleParams:
    """
    Retrieve a vehicle instance from the fleet registry.

    Args:
        vehicle_id: Registry key (e.g., 'volkswagen_31320').

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


def refresh_fleet() -> None:
    """Invalidate the preset cache so newly persisted models become visible.

    Call after db_manager.save_vehicle() (or any preset write) — the cache
    is rebuilt from the database/JSON on the next fleet access. The cache
    also self-refreshes every _CACHE_TTL_S seconds.
    """
    global _cache_loaded_at
    _JSON_MODELS_CACHE.clear()
    _cache_loaded_at = 0.0


__all__ = [
    "get_vehicle_by_id",
    "list_vehicles",
    "list_vehicle_ids",
    "refresh_fleet",
    "fleet_source",
]

