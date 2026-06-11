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
# Install dependencies
pip install -r requirements.txt

# Generate Interlagos track from GPS waypoints (first run only)
python src/tracks/generate_br_tracks.py

# Launch the Streamlit dashboard
streamlit run src/visualization/interface.py
```

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
