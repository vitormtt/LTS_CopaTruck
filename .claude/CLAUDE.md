# CLAUDE.md — LapTimeSimulator_CopaTruck
# Version: 2.0 | 2026-04-15
# Migrated from root CLAUDE.md — context isolation: do not assume previous session state

---

## Project

| Field | Value |
|-------|-------|
| Repository | github.com/vitormtt/LapTimeSimulator_CopaTruck |
| Purpose | Lap time simulator for Copa Truck — SARU Dynamics product |
| Stack | Python 3.x, NumPy, SciPy, HDF5, Streamlit |
| Partnership | Técnico — Pérez (post-graduation) |
| Local path | `C:\Users\vitor\OneDrive\Desktop\Pastas\LapTimeSimulator_V2` |

## Simulation Model

- **Bicycle Model 2-DOF** with lateral, longitudinal, engine, transmission and brake dynamics
- **Two-Pass Solver**: Forward (max acceleration) → Backward (braking to corner entry speed)
- Default preset: Copa Truck — Mercedes-Benz Actros 600 kW (diesel, peak torque ~1300 RPM)
- **Never alter the two-pass solver without cross-validation against known lap times.**

## Directory Structure

```
LapTimeSimulator_CopaTruck/
├── .claude/
│   ├── CLAUDE.md                    # This file
│   └── skills/
│       ├── python-saru-standards.md   # SARU Python conventions
│       ├── python-solver-workflow.md  # Two-pass solver rules
│       └── python-telemetry.md        # Telemetry pipeline
├── src/
│   ├── simulation/    ← lap_time_solver.py — core solver (two-pass)
│   ├── vehicle/       ← VehicleParams and sub-dataclasses
│   ├── tracks/        ← HDF5 reader/writer, TUM FTM integration
│   ├── visualization/ ← Streamlit interface
│   ├── optimization/  ← setup optimization (future)
│   └── results/       ← exported .csv telemetry
├── tracks/          ← circuit files (.hdf5)
├── data/            ← vehicle presets (.json)
├── tests/
├── requirements.txt
└── pyproject.toml
```

## OOP Architecture

### Dataclasses (SSoT for all vehicle data)
```python
VehicleMassGeometry | TireParams | AeroParams
EngineParams | TransmissionParams | BrakeParams
VehicleParams  # composes all above — never hardcode vehicle constants outside it
```
- `__repr__` mandatory on all dataclasses
- Default preset: `copa_truck_2dof_default()`

### ABCs (interchangeable subsystems)
```python
TireModel(ABC)   ← PacejkaModel, LinearTireModel
Solver(ABC)      ← TwoPassSolver
TrackLoader(ABC) ← HDF5Loader, TUMFTMLoader
```

### Composition Rule
- `LapSimulator` **contains** Vehicle, Track, Solver — never inherits

## SSoT — Parameters

| Source | Content |
|--------|---------|
| `data/<name>.json` | Vehicle preset (serialized VehicleParams) |
| `tracks/<name>.hdf5` | Circuit geometry |

## Active Skills

- `.claude/skills/python-saru-standards.md` — PEP 8, type hints, dataclass, ABC rules
- `.claude/skills/python-solver-workflow.md` — two-pass method, validation gates
- `.claude/skills/python-telemetry.md` — telemetry ingestion and export pipeline

## Status (2026)

- Core solver: complete and validated (18/18 tests passing)
- Pending: frontend customization + vehicle params from Pérez
- Roadmap: 3-DOF roll dynamics, genetic algorithm setup optimization, Pacejka tire model

## Golden Rules

1. Never hardcode vehicle or track parameters
2. Never alter the two-pass solver without cross-validation
3. pytest must pass 100% before any commit
4. ABCs must be fully implemented
5. Keep this file up to date — include a CLAUDE.md diff when proposing structural changes
