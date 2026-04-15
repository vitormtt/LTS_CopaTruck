---
name: python-saru-standards
description: |
  Enforces SARU Dynamics Python coding conventions across all lap time
  simulator and analysis projects (CopaTruck, StockCar, Generic, LapAnalyzer).
  Activate when creating or reviewing any Python file: models, solvers,
  pipelines, tests, or configuration modules.
---

## Module Template

```python
"""
Module: <name>
Description: <one-line purpose>
Reference: <Pacejka 2012 / SAE XXXX / internal>
Author: Vitor Toledo | SARU Dynamics
Updated: YYYY-MM-DD
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Classes | PascalCase | `TwoPassSolver` |
| Functions / variables | snake_case | `compute_lateral_force` |
| Constants | UPPER_CASE | `G_ACCEL = 9.81` |
| Private attributes | `_` prefix | `self._state` |
| Abstract base classes | Suffix `ABC` or use ABC directly | `TireModel(ABC)` |

## Type Hints & Docstrings

- Type hints required on ALL public function and method signatures
- Docstrings: Google Style on all classes and public methods
- `__repr__` mandatory on all dataclasses

## Dataclass Rules

- Use `@dataclass` for all parameter and result structures
- No hardcoding inside dataclass defaults — use `field(default_factory=...)`
- Serialization: JSON (vehicle presets) or YAML (configs) or HDF5 (tracks)
- `VehicleParams` is SSoT — never duplicate vehicle constants elsewhere

## ABC Rules

- Every interchangeable subsystem gets an ABC (TireModel, Solver, TrackLoader)
- No abstract method may be left unimplemented in any subclass
- Switching implementation must require zero changes outside the module

## Composition Rule

- `LapSimulator` **contains** Vehicle, Track, Solver — never inherits them
- `setup_optimizer` **wraps** LapSimulator — optimization loop only
- `weekend_manager` **uses** LapSimulator — orchestration only

## Module Boundaries (StockCar / Generic)

| Module | Owns | Must NOT contain |
|--------|------|------------------|
| `core/` | Physics, solver | I/O, UI, strategy |
| `data_pipeline/` | Ingest, validate | Simulation logic |
| `kpis/` | KPI computation | Raw simulation |
| `setup_optimizer/` | Optimisation loop | Physics model |
| `weekend_manager/` | Session workflow | Lap physics |

## Prohibited Patterns

- No magic numbers — all constants in dataclass fields or named module-level constants
- No hardcoding of vehicle, track or season values in Python source
- No multiple inheritance — Mixins only for orthogonal behaviours
- `__init__.py` exports only the public interface

## Testing

- `pytest tests/` must pass 100% before any commit
- Unit tests: `tests/test_<module>.py`
- Integration tests: `tests/test_integration.py`
- Never propose a commit with failing tests

## Git — Conventional Commits

```
feat     — new feature or simulation capability
fix      — bug fix or parameter correction
refactor — restructure without behaviour change
sim      — simulation result update or scenario change
docs     — README, comments, CLAUDE.md, reports
chore    — cleanup, config, tooling, dependencies
test     — add or update validation / regression tests
perf     — performance improvement (solver speed, memory)
```
