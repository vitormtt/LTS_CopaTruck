"""
Vehicle package — exports all public symbols used by the solver and interface.
"""

from .parameters import (
    VehicleParams,
    VehicleMassGeometry,
    TireParams,
    AeroParams,
    EngineParams,
    TransmissionParams,
    BrakeParams,
    copa_truck_2dof_default,
    validate_vehicle_params,
)
from .setup import VehicleSetup, apply_setup, apply_setup_to_params, get_default_setup
from .fleet import get_vehicle_by_id, list_vehicles, list_vehicle_ids

__all__ = [
    # parameters
    "VehicleParams",
    "VehicleMassGeometry",
    "TireParams",
    "AeroParams",
    "EngineParams",
    "TransmissionParams",
    "BrakeParams",
    "copa_truck_2dof_default",
    "validate_vehicle_params",
    # setup
    "VehicleSetup",
    "apply_setup",
    "apply_setup_to_params",
    "get_default_setup",
    # fleet
    "get_vehicle_by_id",
    "list_vehicles",
    "list_vehicle_ids",
]
