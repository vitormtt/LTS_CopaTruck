# LapTimeSimulator — Copa Truck

Quasi-steady-state (QSS) lap time simulator for motorsport vehicles. Developed by SARU Dynamics.

Supports the Copa Truck fleet (diesel race trucks), with setup sweeps, batch simulation, setup optimization and real telemetry comparison.

---

## Architecture

The solver is **self-contained**: all physics (load transfer, aero, ARB, gear selection, tyre thermal, BSFC fuel, brake fade) lives inside `lap_time_solver.py` and operates directly on `VehicleParams`. An earlier parallel modular architecture (BicycleVehicle2DOF, ThermalPacejkaTire, Pneumatic/HydraulicBrake, driver model, standalone optimizer, KPI dashboard) had no live callers and is archived under `_archive/dead_modules/` for reference.

```
src/
├── simulation/
│   ├── lap_time_solver.py      ← QSS forward-backward solver with internal physics;
│   │                              run_simulation() + run_bicycle_model()
│   ├── simulation_modes.py     ← SimulationMode enum + SimulationConfig dataclass
│   └── telemetry.py            ← telemetry channel definitions
├── vehicle/
│   ├── parameters.py           ← VehicleParams + sub-dataclasses (SSoT) + validate_vehicle_params()
│   ├── setup.py                ← VehicleSetup; apply_setup(); ARB + wing + tyre pressure model
│   ├── fleet/                  ← fleet registry; loads validated presets from data/vehicle_models.json
│   ├── engine.py               ← ICEEngine; torque curve interpolation (used by the torque curve editor;
│   │                              mirrored by the solver's BSFC fuel model)
│   ├── transmission.py         ← Transmission; gear selection
│   └── units.py                ← psi↔bar conversion helpers
├── tracks/
│   ├── hdf5.py                 ← CircuitHDF5Reader / Writer (tracks/*.hdf5, tracks/custom/)
│   ├── circuit.py              ← CircuitData dataclass
│   ├── generate_br_tracks.py   ← build_interlagos_real() from GPS waypoints
│   ├── telemetry_converter.py  ← AiM .xrk/.xrz → CSV (requires libxrk)
│   └── osm.py / tumftm.py      ← OSM and TUM FTM track loaders
└── visualization/
    ├── interface.py             ← Streamlit app entry point
    └── components/              ← one module per UI page:
        Parameters · Track · Simulation · Batch Simulation · Results ·
        Compare · Optimization  (+ torque curve editor, shared helpers)

_archive/
├── dead_modules/                ← archived parallel architecture (no live callers)
└── scripts/                     ← orphan root scripts (legacy Porsche e2e, module probes)
```

### Simulation model

**Bicycle model 2-DOF** with QSS forward-backward solver:

1. **Forward pass** — maximum acceleration limited by traction (engine + grip) and lateral speed limit at each corner.
2. **Backward pass** — braking to not exceed corner-entry speed.
3. **Time/thermal pass** — cumulative lap time, tyre temperature, fuel consumption.

Physics (internal to the solver):
- Longitudinal load transfer (pitch: squat on acceleration, dive on braking)
- Aerodynamic downforce and drag updating normal load and grip
- ARB load-sensitivity model: lateral load transfer distributed front/rear by ARB stiffness ratio; grip penalty proportional to per-axle overload
- Diesel torque curve (interpolated map, editable per model in the UI)
- Gear selection maximising drive force within RPM band
- Brake bias coupled to longitudinal load transfer (first-axle-lockup cap)
- Tyre thermal model (bulk temperature and hot pressure estimate)
- **Dynamic fuel consumption**: BSFC × instantaneous power × dt; burned mass feeds back into vehicle dynamics
- Brake disc thermal model with temperature-dependent fade (`ENDURANCE_THERMAL`)

### Simulation modes

| Mode | Description |
|------|-------------|
| `QUALIFYING` | Single lap from equilibrium speed (default) |
| `STANDING_START` | Lap from rest with clutch-ramp wheelspin model |
| `ENDURANCE_THERMAL` | Qualifying-style lap with brake disc heat model and temperature-dependent brake fade |
| `FLYING_LAP` | Lap from prescribed entry speed (`v_entry_kmh`) |
| `ROLLING_START` | Alias for `FLYING_LAP` (backward compatibility) |

### Vehicle setup (`VehicleSetup`)

Discrete + continuous parameters applied to a base `VehicleParams` before solving:

| Parameter | Range | Effect |
|-----------|-------|--------|
| `arb_front` | 1–7 | Front ARB stiffness [50–420 kNm/rad] |
| `arb_rear` | 1–7 | Rear ARB stiffness [40–340 kNm/rad] |
| `wing_position` | 1–9 | ΔCd and ΔCl_rear |
| `tyre_pressure` | 1.4–2.4 bar | Scales cornering stiffness and friction coefficient |
| `brake_bias` | −2.0–0.0 | Front brake balance offset |

---

## Fleet

Presets are defined in `data/vehicle_models.json` and validated on load (`validate_vehicle_params`):

| ID | Vehicle | Power |
|----|---------|-------|
| `volkswagen_31320` | VW 31320 (Copa Truck Racing) | 850 kW |
| `scania_r480` | Scania R480 (Racing Tuned) | 880 kW |
| `volvo_fh16` | Volvo FH16 (Racing Tuned) | 900 kW |

Code default: `copa_truck_2dof_default()` — Mercedes-Benz Actros 600 kW, 12-speed automatic, `gear_min=4`.

---

## Quick start

```bash
# 1. Setup the isolated environment (uv, from pyproject.toml)
uv sync                    # creates .venv with all deps
# fallback: python -m venv .venv && .venv/bin/pip install -e .

# 2. Launch the dashboard
.venv/bin/streamlit run src/visualization/interface.py
# (with the venv activated, just: streamlit run src/visualization/interface.py)
```

Then open **http://localhost:8501** in the browser. The app runs fully on
the local JSON fallback (`data/vehicle_models.json`) — no database required.

### How to visualize a lap

Walk the pages left-to-right in the sidebar:

1. **Parameters** — pick the vehicle preset, tweak params, **Save**.
2. **Track** — select a circuit (Cascavel / Interlagos); optional racing-line toggle.
3. **Simulation** — choose the mode (Qualifying / Standing start) and **Run**.
4. **Results** — telemetry dashboard: speed map, G-G diagram, gear/RPM, sector
   timing, PDF/CSV/HTML export (charts grouped in tabs).
5. **Telemetry Overlay** / **Race Report** — compare the sim against real `.xrk`
   laps (speed trace, Δt, grip factors).
6. **Optimization** — sweep wing × tyre pressure (Grid search or Differential
   Evolution) for the fastest setup.

### Docker (app + PostgreSQL)

The stack ships as two containers: `app` (Streamlit UI + simulation core)
and `db` (PostgreSQL 16, schema auto-applied on first start). Vehicle
presets and simulation results are stored in Postgres with a transparent
JSON fallback (`src/database/db_manager.py`) when the database is offline.

```bash
cp .env.example .env   # set DB credentials (compose refuses to start without it)
make up                # build + start db and app (dev hot-reload via override)
make seed              # load fleet presets from data/vehicle_models.json into Postgres
make logs-app          # follow the Streamlit logs — UI at http://localhost:8501
make down              # stop (down-clean also drops the db volume)
```

`docker-compose.override.yml` bind-mounts `src/`, `data/` and `tracks/`
for development; use `docker compose -f docker-compose.yml up` for a
production-like run from the baked image. The `base` stage in the
`Dockerfile` is the shared foundation for a future REST API service
(`FROM base AS api`) once the frontend is split out of this repo.

### Run a simulation from Python

```python
from src.simulation.lap_time_solver import run_simulation
from src.simulation.simulation_modes import SimulationConfig, SimulationMode
from src.vehicle.fleet import get_vehicle_by_id
from src.vehicle.setup import get_default_setup
from src.tracks.hdf5 import CircuitHDF5Reader

circuit, _ = CircuitHDF5Reader("tracks/interlagos.hdf5").read_circuit()
vehicle    = get_vehicle_by_id("volkswagen_31320")
config     = SimulationConfig(mode=SimulationMode.QUALIFYING, setup=get_default_setup())

result = run_simulation(config, vehicle, circuit)
print(f"Lap time: {result.lap_time:.2f} s")
result.save_csv("out.csv")
```

---

## Data files

| Path | Content |
|------|---------|
| `tracks/interlagos.hdf5` | Interlagos centerline (GPS reference) |
| `tracks/cascavel.hdf5` | Cascavel centerline |
| `tracks/custom/` | User-saved tracks from the UI |
| `data/vehicle_models.json` | Vehicle preset definitions (validated on load) |

---

## References

- Brayshaw, D.L. & Harrison, M.F. (2005). A quasi steady state approach to race car lap simulation. *Proc. IMechE Part D*, 219(3), 383–394.
- Segers, J. (2014). *Analysis Techniques for Racecar Data Acquisition*, 2nd ed. SAE International.
- Pacejka, H.B. (2012). *Tyre and Vehicle Dynamics*, 3rd ed. Butterworth-Heinemann.
- Gillespie, T.D. (1992). *Fundamentals of Vehicle Dynamics*. SAE International.
- Pi Toolbox Apostila de Treinamento — Porsche Carrera Cup Brasil (2014).
