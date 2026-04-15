# CLAUDE.md — LapTimeSimulator_CopaTruck
# Project: Lap time simulator — Copa Truck (SARU Dynamics product)
# Cluster: SARU Python | Partner: Pérez (post-graduation)
# Context isolation: do not assume state from any previous session
# Note: root CLAUDE.md is kept for backwards compatibility — this file takes precedence

---

## 1. PROJECT

| Field | Value |
|-------|-------|
| Repository | github.com/vitormtt/LapTimeSimulator_CopaTruck |
| Python | 3.x |
| Stack | NumPy, SciPy, HDF5, Streamlit |
| Local path | C:\Users\vitor\OneDrive\Desktop\Pastas\LapTimeSimulator_V2 |
| Status | Core solver complete (18/18 tests passing) |

---

## 2. MODEL

**Bicycle Model 2-DOF** + extensions:
- Lateral: cornering forces (Cf, Cr)
- Longitudinal: traction limited by grip + aero drag
- Engine: diesel torque curve (peak ~1300 RPM)
- Transmission: automatic gear selection (1200–2200 RPM band)
- Brakes: friction circle (max deceleration respecting a_lat)

**Solver: Two-Pass (Forward-Backward)**
- Forward pass: max acceleration respecting traction and lateral limits
- Backward pass: braking to not exceed corner entry speed
- **Never alter the two-pass method without cross-validation against known lap times.**

---

## 3. STRUCTURE

```
LapTimeSimulator_CopaTruck/
├── src/
│   ├── simulation/      ← lap_time_solver.py (core solver, two-pass)
│   ├── vehicle/         ← VehicleParams and sub-dataclasses
│   ├── tracks/          ← HDF5 reader/writer, TUM FTM integration
│   ├── visualization/   ← Streamlit interface (interface.py)
│   ├── optimization/    ← setup optimization (future)
│   └── results/         ← exported .csv telemetry
├── tracks/             ← circuit files (.hdf5)
├── data/               ← vehicle presets (.json)
├── tests/              ← pytest — must pass 100% before any push
├── requirements.txt
├── pyproject.toml
└── .claude/
    ├── CLAUDE.md        ← this file (canonical)
    └── skills/
        ├── python-saru-standards.md
        ├── python-solver-workflow.md
        └── python-telemetry.md
```

---

## 4. OOP ARCHITECTURE

```python
# Dataclasses (SSoT for parameters)
@dataclass VehicleMassGeometry  # mass, wheelbase, CG, inertias
@dataclass TireParams            # Cf, Cr, mu, wheel radius
@dataclass AeroParams            # Cd, frontal area, Cl
@dataclass EngineParams          # power, torque, RPM
@dataclass TransmissionParams    # gears, ratios, final drive
@dataclass BrakeParams           # max force, balance, deceleration
@dataclass VehicleParams         # composes all sub-dataclasses

# ABCs (interchangeable subsystems)
class TireModel(ABC)    ← PacejkaModel, LinearTireModel
class Solver(ABC)       ← TwoPassSolver
class TrackLoader(ABC)  ← HDF5Loader, TUMFTMLoader
```

- `LapSimulator` contains `VehicleParams`, `Track`, `Solver` — never inherits
- Default preset: `copa_truck_2dof_default()` (Mercedes-Benz Actros 600 kW)
- `__repr__` mandatory on all dataclasses

---

## 5. SSOT — PARAMETERS

| Source | Content |
|--------|---------|
| `data/<name>.json` | Vehicle preset (serialized VehicleParams) |
| `tracks/<name>.hdf5` | Circuit geometry (centerline, boundaries, width) |

Never hardcode vehicle or track values — always load from JSON or HDF5.

---

## 6. GOLDEN RULES

1. Never hardcode vehicle or track parameters.
2. Never alter the two-pass solver without cross-validation.
3. pytest must pass 100% before any commit is proposed.
4. ABCs must be fully implemented — no abstract method left unimplemented.
5. Keep this file up to date — include CLAUDE.md diff when proposing structural changes.

---

## 7. CODE STANDARDS

See `.claude/skills/python-saru-standards.md` for full conventions.

### Git — Conventional Commits
```
feat / fix / refactor / sim / docs / chore / test / perf
```

---

## 8. STATUS (2026)

- Core solver: complete and validated (18/18 tests passing)
- Pending: frontend customization + vehicle params from Pérez
- Roadmap: 3-DOF roll dynamics, genetic algorithm setup optimization, Pacejka tire model
