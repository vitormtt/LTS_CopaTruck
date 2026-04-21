# LapTimeSimulator_CopaTruck

## Context
- Lap time simulator for Copa Truck — SARU Dynamics product
- Technical partnership: Pérez (post-graduation)
- Stack: Python 3.x, Streamlit, NumPy, SciPy, HDF5
- GitHub: vitormtt/LapTimeSimulator_CopaTruck
- Local path: `C:\Users\vitor\OneDrive\Desktop\Pastas\LapTimeSimulator_V2`

> **This file (`CLAUDE.md`) is a living document** — update it whenever architecture, conventions, or sequences change.

---

## Project Architecture

```
LapTimeSimulator_CopaTruck/
├── src/
│   ├── simulation/          ← lap_time_solver.py — core solver (two-pass)
│   ├── vehicle/             ← VehicleParams and sub-dataclasses
│   ├── tracks/              ← HDF5 reader/writer, TUM FTM integration
│   ├── visualization/       ← Streamlit interface (interface.py)
│   ├── optimization/        ← setup optimization (future)
│   └── results/             ← exported .csv telemetry
├── tracks/                  ← circuit files (.hdf5)
├── data/                    ← vehicle presets (.json)
├── tests/                   ← pytest — must pass 100% before any push
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## Simulation Model

**Bicycle Model 2DOF** with extensions:
- Lateral dynamics: cornering forces (Cf, Cr)
- Longitudinal dynamics: traction limited by grip + aerodynamic drag
- Engine: realistic torque curve (diesel peak ~1300 RPM)
- Transmission: automatic gear selection to maintain 1200–2200 RPM
- Brakes: friction circle (max deceleration respecting a_lat)

### Forward-Backward Solver (Two-Pass)
1. **Forward pass**: maximum acceleration respecting traction and lateral velocity limits
2. **Backward pass**: braking to not exceed corner entry speed limits
- **Never alter the two-pass method without cross-validation against known lap times.**

---

## OOP Architecture

### Dataclasses (data with validation)
```python
@dataclass
class VehicleMassGeometry:  # mass, wheelbase, CG, inertias
@dataclass
class TireParams:           # Cf, Cr, mu, wheel radius
@dataclass
class AeroParams:           # Cd, frontal area, Cl
@dataclass
class EngineParams:         # power, torque, RPM
@dataclass
class TransmissionParams:   # gears, ratios, final drive
@dataclass
class BrakeParams:          # max force, balance, deceleration
@dataclass
class VehicleParams:        # composes all sub-dataclasses above
```
- `__repr__` mandatory on all dataclasses.
- `VehicleParams` is the SSoT for vehicle data — never hardcode vehicle constants outside it.
- Default preset: `copa_truck_2dof_default()` (Mercedes-Benz Actros 600 kW).

### ABCs (interchangeable subsystems)
```python
class TireModel(ABC):       ← PacejkaModel, LinearTireModel
class Solver(ABC):          ← TwoPassSolver (extensible)
class TrackLoader(ABC):     ← HDF5Loader, TUMFTMLoader
```
- ABCs enforce interface contracts — no subclass may leave abstract methods unimplemented.
- Switching tire model or solver must not require changes outside the respective module.

### Composition Rule
- `LapSimulator` **contains** `VehicleParams`, `Track`, `Solver` — never inherits from them.
- Inheritance only for genuine IS-A relationships.

---

## SSoT — Parameters

| Source | Content |
|--------|---------|
| `data/<name>.json` | Vehicle preset (serialized `VehicleParams`) |
| `tracks/<name>.hdf5` | Circuit geometry (centerline, boundaries, width) |

- **Never hardcode vehicle or track values** — always load from JSON or HDF5.
- New vehicle: implement via `VehicleParams` dataclass and save with `.save_to_json()`.
- New circuit: implement via `CircuitData` and write with `CircuitHDF5Writer`.

---

## Circuit Format (HDF5)

Compressed HDF5 with:
- `centerline_x`, `centerline_y`
- Left/right boundaries
- Track width
- Metadata: name, length, coordinate system

Sources: TUM FTM (`src/tracks/tumftm.py`), custom generators (`src/tracks/generator.py`).

---

## Code Standards

### Python — General
- PEP 8 mandatory
- Type hints on all functions and methods
- Docstrings: Google Style (class + all public methods)
- No magic numbers — all constants in dataclass fields or named module-level constants
- No hardcoding of vehicle or track values

### Python — OOP
- `@dataclass` for data structures with validation
- `ABC` for interchangeable subsystem interfaces
- Private attributes prefixed with `_`; public interface via `@property`
- `__repr__` and `__str__` on all data classes
- Avoid multiple inheritance; use Mixins only for orthogonal behaviors
- One module per physical or functional subsystem
- `__init__.py` exports only the public interface

### Testing
- `pytest tests/` must pass 100% before any commit
- Unit tests per class in `tests/test_<module>.py`
- Never push with failing tests

### Git — Conventional Commits
```
feat:     new feature or simulation capability
fix:      bug fix or parameter correction
refactor: code restructure without behavior change
sim:      simulation result update or scenario change
docs:     README, comments, CLAUDE.md, reports
chore:    cleanup, config, tooling, dependencies
test:     add or update validation/regression tests
perf:     performance improvement (solver speed, memory)
```

---

## Status (2026)
- Core solver: complete and validated (18/18 tests passing)
- Pending: frontend customization + vehicle params from Pérez
- Roadmap: 3DOF roll dynamics, genetic algorithm setup optimization, Pacejka tire model, multi-lap comparison

---

## Golden Rules for Claude

1. **Never hardcode vehicle or track parameters** — all values via `VehicleParams` JSON or HDF5.
2. **Never alter the two-pass solver** without cross-validation against known lap times.
3. **pytest must pass 100%** before any commit is proposed.
4. **ABCs must be fully implemented** — no abstract method left unimplemented in subclasses.
5. **Keep this file up to date** — when proposing structural changes, include a `CLAUDE.md` diff.
