# Architecture — LapTimeSimulator_CopaTruck

> SoT técnico do repo. CLAUDE.md aponta para cá; não duplicar arquitetura no CLAUDE.md.
> Última atualização: 2026-07-10 (auditoria de docs; árvore + defaults físicos).

## Project Structure

```
LapTimeSimulator_CopaTruck/
├── src/
│   ├── simulation/          ← lap_time_solver.py (two-pass QSS) ·
│   │                          simulation_modes.py · telemetry.py (math channels)
│   ├── vehicle/             ← parameters.py (VehicleParams) · setup.py ·
│   │                          brake_hardware.py (Limpert) · tire_model.py (MF viz) ·
│   │                          transmission_curves.py (design viz) · fleet/ · units.py
│   ├── analysis/            ← derived channels: brake_lockup.py ·
│   │                          handling_balance.py · driver_report.py · overlay.py ·
│   │                          race_report.py
│   ├── tracks/              ← hdf5.py · racing_line.py (min-curvature, vehicle-width
│   │                          corridor) · generator.py (TUM FTM/OSM) · circuit.py
│   ├── database/            ← PostgreSQL manager + schema (JSON fallback)
│   ├── visualization/       ← interface.py (router) · theme.py · components/
│   └── results/             ← exported .csv telemetry
├── tracks/                  ← circuit files (.hdf5)
├── data/                    ← vehicle presets (.json) — SINGLE preset
│                              volkswagen_31320 (merged 2026-07-10)
├── tests/                   ← pytest — must pass 100% before any push
├── docs/                    ← ver docs/README.md (índice + status)
├── Dockerfile / docker-compose.yml / Makefile
├── pyproject.toml           ← deps + ruff + mypy (dev group)
└── README.md
```

## Physical defaults (2026-07-10)

- **Racing line SEMPRE é o driving path** (`use_racing_line` default True;
  False = baseline de debug na centerline). O corredor é estreitado pela
  largura estrutural do veículo (bitola + 1 seção de pneu) — veículos
  diferentes geram linhas diferentes; cache por largura.
- **Qualifying = flying lap** (`use_flying_lap_start` default True, BC
  periódica, v0 ≈ velocidade de saída da volta).
- **Freio derivado de hardware** quando blocos `brake_hw_*` presentes no
  preset (Limpert; Knorr SN7 + Fras-le PD/116 researched). Grip-limited.
- **abs_enabled=False** (Copa Truck sem ABS) com modulação bias-aware.
- ⚠️ µ=1.6 é fudge exposto (−8.7 s vs âncora Cascavel) — recalibração via
  pipeline track/µ (docs/Validação de Lap Sim.md) é o próximo épico.

## Containers & Database

- Stack: `db` (PostgreSQL 16-alpine, schema applied via initdb) + `app`
  (Streamlit + core). Config flows exclusively through `.env`
  (`DB_USER/DB_PASSWORD/DB_NAME/DB_PORT/APP_PORT`) — never hardcode
  credentials in compose files.
- **Relational vehicle schema**: one typed table per subsystem mirroring
  the `VehicleParams` dataclasses (`vehicle_mass_geometry/tires/engine/
  transmission/brakes/aero/fuel` 1:1 + `vehicle_gear_ratios` and
  `vehicle_torque_curve` 1:N). The flat solver-dict contract is preserved
  by `src/database/vehicle_mapping.py` (declarative decompose/recompose).
  Legacy JSONB databases are converted with `make migrate` (idempotent).
- `src/database/db_manager.py` reads `DB_*` env vars and falls back to
  JSON files in `data/` when Postgres is unreachable — the app must keep
  working with no database.
- The fleet cache (`src/vehicle/fleet`) self-refreshes every 5 s (TTL),
  so external edits (psql, seed, another session) reach the UI without a
  restart; `refresh_fleet()` forces it.
- The `base` image stage is the anchor for a future `api` service (REST)
  when the frontend is split out — add `FROM base AS api`, do not fork a
  second dependency stack.

## Simulation Model

**Bicycle Model 2DOF** with extensions:
- Lateral dynamics: cornering forces (Cf, Cr)
- Longitudinal dynamics: traction limited by grip + aerodynamic drag
- Engine: realistic torque curve clamped so T·ω ≤ max_power; per-model
  default curves in `data/vehicle_models.json`, editable in the UI
  (`components/torque_curve.py`)
- Transmission: automatic gear selection with downshift hysteresis,
  driveline efficiency and shift-time traction cut (partial-step)
- Tires: quasi-static per-axle load transfer (k_roll split, track
  widths, h_cg), load-sensitive mu (`_S_LOAD`), Pacejka D as friction
  scale, slip-angle channels from Cf/Cr (steady-state bicycle steering)
- Traction: REAR axle limited (RWD) with longitudinal load transfer
- Brakes: friction circle + bias/lockup cap + ABS/driver modulation +
  first-order response-time loss
- Yaw: quasi-transient yaw-rate cap makes Iz live in chicanes
- Fuel: dynamic consumption = BSFC × instantaneous power × dt (output,
  not input); burned mass feeds back into vehicle dynamics
- Thermal braking (`ENDURANCE_THERMAL` mode): lumped disc heat model
  with temperature-dependent fade — wraps the two-pass solver without
  modifying it (fade-disabled output is bit-identical to qualifying)
- Units: psi↔bar conversions centralized in `src/vehicle/units.py`

### Forward-Backward Solver (Two-Pass)
1. **Forward pass**: maximum acceleration respecting traction and lateral velocity limits
2. **Backward pass**: braking to not exceed corner entry speed limits
- **Never alter the two-pass method without cross-validation against known lap times.**

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

## SSoT — Parameters

| Source | Content |
|--------|---------|
| `data/<name>.json` | Vehicle preset (serialized `VehicleParams`) |
| `tracks/<name>.hdf5` | Circuit geometry (centerline, boundaries, width) |

- **Never hardcode vehicle or track values** — always load from JSON or HDF5.
- New vehicle: implement via `VehicleParams` dataclass and save with `.save_to_json()`.
- New circuit: implement via `CircuitData` and write with `CircuitHDF5Writer`.

## Circuit Format (HDF5)

Compressed HDF5 with:
- `centerline_x`, `centerline_y`
- Left/right boundaries
- Track width
- Metadata: name, length, coordinate system

Sources: TUM FTM (`src/tracks/tumftm.py`), custom generators (`src/tracks/generator.py`).

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
- `python3 -m pytest` must pass 100% before any commit (includes unit and solver regression tests)
- Unit tests per class in `tests/test_<module>.py`
- Solver regression baselines checked by `tests/test_solver_regression.py`
- To regenerate solver baselines (only after verified, cross-validated solver accuracy tuning):
  `python3 tests/generate_regression_baselines.py`
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
