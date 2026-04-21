# LapTimeSimulator — Copa Truck / Carrera Cup

Quasi-steady-state lap time simulator for motorsport vehicles. Developed by SARU Dynamics.

Supports Copa Truck (diesel, pneumatic brakes) and Porsche Carrera Cup Brasil fleet (GT3 991.1, 991.2, 992.1), with a modular architecture designed for multi-vehicle comparison, setup optimization, and real telemetry validation.

---

## Architecture

```
src/
├── simulation/
│   ├── lap_time_solver.py      ← GGV forward-backward solver; run_simulation() + run_bicycle_model()
│   ├── simulation_modes.py     ← SimulationMode enum + SimulationConfig dataclass
│   ├── driver_model.py         ← DriverInputs dataclass; throttle/brake/steering derivation
│   ├── telemetry.py            ← telemetry channel definitions
│   └── validation.py           ← simulation vs. real telemetry comparator (Pi Toolbox / MoTeC)
├── vehicle/
│   ├── parameters.py           ← VehicleParams + sub-dataclasses (SSoT)
│   ├── setup.py                ← VehicleSetup; apply_setup(); ARB + wing + tyre pressure model
│   ├── fleet/                  ← porsche_gt3_991_1, 991_2, 992_1 presets
│   ├── engine.py               ← ICEEngine; torque curve interpolation
│   ├── transmission.py         ← Transmission; gear selection
│   ├── tires.py                ← ThermalPacejkaTire
│   ├── brakes.py               ← PneumaticBrake
│   └── vehicle_model.py        ← BicycleVehicle2DOF; composed vehicle object
├── tracks/
│   ├── hdf5.py                 ← CircuitHDF5Reader / Writer
│   ├── circuit.py              ← CircuitData dataclass
│   ├── generate_br_tracks.py   ← build_interlagos_real() from GPS waypoints
│   └── osm.py / tumftm.py      ← OSM and TUM FTM track loaders
├── optimization/
│   └── optimization.py         ← speed-profile optimizer (scipy); setup sweep
└── visualization/
    ├── interface.py             ← Streamlit dashboard
    ├── kpi_dashboard.py         ← KPI tables and lap-time comparison charts
    └── track_plotter.py         ← speed map and track overlay plots
```

### Simulation model

**Bicycle model 2-DOF** with GGV forward-backward solver:

1. **Forward pass** — maximum acceleration limited by traction (engine + grip) and lateral speed limit at each corner.
2. **Backward pass** — braking to not exceed corner-entry speed.
3. **Time/thermal pass** — cumulative lap time, tyre temperature, fuel consumption.

Physics extensions:
- Longitudinal load transfer (pitch: squat on acceleration, dive on braking)
- Aerodynamic downforce and drag updating normal load and grip
- ARB load-sensitivity model: lateral load transfer distributed front/rear by ARB stiffness ratio; grip penalty proportional to per-axle overload
- Diesel torque curve (interpolated map or parametric) / GT3 torque curve
- Gear selection maximising drive force within RPM band
- Tyre thermal model (bulk temperature and hot pressure estimate)
- Fuel consumption from power demand

### Simulation modes

| Mode | Description |
|------|-------------|
| `QUALIFYING` | Single lap from equilibrium speed (default) |
| `FLYING_LAP` | Lap from prescribed entry speed (`v_entry_kmh`) |
| `STANDING_START` | Lap from rest with clutch-ramp wheelspin model |
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

| ID | Vehicle | Power |
|----|---------|-------|
| `porsche_991_1` | Porsche 911 GT3 Cup (991 Phase 1) | 338 kW |
| `porsche_991_2` | Porsche 911 GT3 Cup (991 Phase 2) | 338 kW |
| `porsche_992_1` | Porsche 911 GT3 Cup (992 Phase 1) | 373 kW |

Copa Truck default: `copa_truck_2dof_default()` — Mercedes-Benz Actros 600 kW, 12-speed automatic, `gear_min=4`.

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
vehicle    = get_vehicle_by_id("porsche_991_1")
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
| `data/vehicle_models.json` | Vehicle preset definitions |

---

## References

- Brayshaw, D.L. & Harrison, M.F. (2005). A quasi steady state approach to race car lap simulation. *Proc. IMechE Part D*, 219(3), 383–394.
- Segers, J. (2014). *Analysis Techniques for Racecar Data Acquisition*, 2nd ed. SAE International.
- Pacejka, H.B. (2012). *Tyre and Vehicle Dynamics*, 3rd ed. Butterworth-Heinemann.
- Gillespie, T.D. (1992). *Fundamentals of Vehicle Dynamics*. SAE International.
- Pi Toolbox Apostila de Treinamento — Porsche Carrera Cup Brasil (2014).
