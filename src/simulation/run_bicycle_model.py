"""
Módulo de compatibilidade para execução direta do modelo de bicicleta (QSS).
Reexporta a função run_bicycle_model do solver principal.
"""
from src.simulation.lap_time_solver import run_bicycle_model, run_simulation

__all__ = ["run_bicycle_model", "run_simulation"]
