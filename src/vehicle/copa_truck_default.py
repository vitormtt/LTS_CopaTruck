"""
Parâmetros padrão do caminhão de corrida da Copa Truck.
Exposição direta dos parâmetros calibrados para simulação rápida.
"""
from src.vehicle.parameters import VehicleParams, copa_truck_2dof_default


def copa_truck_default() -> VehicleParams:
    """Retorna os parâmetros padrão calibrados do veículo Copa Truck."""
    return copa_truck_2dof_default()


__all__ = ["copa_truck_default", "copa_truck_2dof_default"]
