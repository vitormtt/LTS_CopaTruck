---
name: python-saru-standards
description: |
  Enforces SARU Dynamics Python coding conventions across all simulator
  and analysis repos (LapTimeSimulator_*, SARU_LapAnalyzer, Lap_Time_Hase).
  Activate when creating or reviewing any .py file, dataclass, ABC, or module.
---

## Module Header (mandatory)

```python
"""
Module: <name>
Description: <one-line purpose>
Reference: <Pacejka 2012 / SAE XXXX / ISO XXXX>
"""
from __future__ import annotations
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Classes | PascalCase | `TwoPassSolver` |
| Functions / variables | snake_case | `compute_corner_speed` |
| Constants | UPPER_CASE | `G_ACCELERATION` |
| Private attributes | `_name` | `_state` |
| ABCs | Noun + `(ABC)` | `TireModel(ABC)` |

## Dataclass Rules

```python
@dataclass
class VehicleParams:
    """
    Single source of truth for vehicle physical parameters.
    Never hardcode vehicle constants outside this class.
    """
    mass: float          # kg
    wheelbase: float     # m
    # ... all fields documented with units
    
    def __repr__(self) -> str: ...
    def __post_init__(self) -> None: ...  # validation
```

- `__repr__` mandatory on all dataclasses
- `__post_init__` for physical range validation
- Serialization via `.json` (vehicle) or `.yaml` (config/season)

## ABC Rules

```python
class TireModel(ABC):
    @abstractmethod
    def compute_force(self, slip: float, Fz: float) -> tuple[float, float]:
        """Compute lateral and longitudinal tire forces."""
        ...
```

- No subclass may leave abstract methods unimplemented
- Swapping subsystems must not require changes outside the respective module

## Type Hints and Docstrings

- Type hints on ALL public function and method signatures
- Google-style docstrings on all public classes and methods:

```python
def compute_corner_speed(self, radius: float, mu: float) -> float:
    """Compute maximum cornering speed for a given radius.

    Args:
        radius: Corner radius in meters.
        mu: Tire-road friction coefficient.

    Returns:
        Maximum speed in m/s.
    """
```

## Module Boundary Rules

| Module | Contains | Never put here |
|--------|---------|----------------|
| `core/` or `src/simulation/` | Physics, solver | I/O, UI, strategy |
| `data_pipeline/` | Ingest, validate | Simulation logic |
| `visualization/` | Streamlit, plots | Physics model |
| `config/` | Parameters, env | Business logic |

## Quality Gates

- `pytest tests/` must pass 100% before any commit
- `ruff check .` must pass with zero errors
- Never push with failing tests
- `__init__.py` exports only the public interface
