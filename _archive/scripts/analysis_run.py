import sys, logging
sys.path.insert(0, '.')
logging.disable(logging.CRITICAL)

import numpy as np
from src.simulation.lap_time_solver import run_simulation
from src.simulation.simulation_modes import SimulationConfig, SimulationMode
from src.vehicle.fleet import get_vehicle_by_id
from src.vehicle.setup import get_default_setup, VehicleSetup
from src.tracks.hdf5 import CircuitHDF5Reader

circuit, meta = CircuitHDF5Reader('tracks/interlagos.hdf5').read_circuit()
print(f"Track: {meta['name'].title()} | {float(meta['length']):.0f} m | {meta['n_points']} pts\n")

print("Fleet @ default setup")
print("-" * 95)
vehicles = ['porsche_991_1', 'porsche_991_2', 'porsche_992_1']
results = {}
for vid in vehicles:
    vp  = get_vehicle_by_id(vid)
    cfg = SimulationConfig(mode=SimulationMode.QUALIFYING, setup=get_default_setup())
    r   = run_simulation(cfg, vp, circuit, save_csv=False)
    results[vid] = r
    print(f"  {vid:<18} {r.lap_time:>7.3f}s  "
          f"Vavg={r.avg_speed_kmh:.1f}  Vmax={r.max_speed_kmh:.1f}  "
          f"Lat={r.peak_lat_g:.2f}g  WOT={r.time_wot_pct:.0f}%  "
          f"Fuel={r.fuel_total_l:.2f}L  Ttyre={r.final_tyre_temp_c:.1f}C")

r_base = results['porsche_991_1']
print()
for vid, r in results.items():
    print(f"  delta {vid}: {r.lap_time - r_base.lap_time:+.3f}s")

print("\nWing sweep (porsche_991_1)")
print("-" * 65)
vp = get_vehicle_by_id('porsche_991_1')
wing_results = []
for w in [1, 3, 5, 7, 9]:
    s   = VehicleSetup(arb_front=4, arb_rear=4, wing_position=w,
                       tyre_pressure=1.8, brake_bias=-1.0, setup_name=f"W{w}")
    cfg = SimulationConfig(mode=SimulationMode.QUALIFYING, setup=s)
    r   = run_simulation(cfg, vp, circuit, save_csv=False)
    wing_results.append((w, r))
    print(f"  Wing {w}  Lap={r.lap_time:.3f}s  Vmax={r.max_speed_kmh:.1f}  dCd={s.wing_delta_cd:+.3f}  dCl={s.wing_delta_cl:+.3f}")
best_w, best_r = min(wing_results, key=lambda x: x[1].lap_time)
print(f"  best wing: {best_w} -> {best_r.lap_time:.3f}s")

print("\nARB front sweep (porsche_991_1, rear=4, wing=5)")
print("-" * 65)
arb_results = []
for af in range(1, 8):
    s   = VehicleSetup(arb_front=af, arb_rear=4, wing_position=5,
                       tyre_pressure=1.8, brake_bias=-1.0, setup_name=f"F{af}")
    cfg = SimulationConfig(mode=SimulationMode.QUALIFYING, setup=s)
    r   = run_simulation(cfg, vp, circuit, save_csv=False)
    arb_results.append((af, r, s))
    print(f"  ARB_F={af}  K={s.arb_front_stiffness/1e3:>5.0f} kNm/rad  Lap={r.lap_time:.3f}s  {s.understeer_tendency}")
best_af, best_r, _ = min(arb_results, key=lambda x: x[1].lap_time)
print(f"  best ARB_F: {best_af} -> {best_r.lap_time:.3f}s")

print("\nTyre pressure sweep (porsche_991_1, ARB 4/4, wing=5)")
print("-" * 55)
pres_results = []
for p_bar in [1.5, 1.6, 1.7, 1.8, 1.9, 2.0, 2.1, 2.2]:
    s   = VehicleSetup(arb_front=4, arb_rear=4, wing_position=5,
                       tyre_pressure=p_bar, brake_bias=-1.0, setup_name=f"P{p_bar}")
    cfg = SimulationConfig(mode=SimulationMode.QUALIFYING, setup=s)
    r   = run_simulation(cfg, vp, circuit, save_csv=False)
    pres_results.append((p_bar, r))
    print(f"  P={p_bar:.1f} bar  Lap={r.lap_time:.3f}s  Vmax={r.max_speed_kmh:.1f}")
best_p, best_r = min(pres_results, key=lambda x: x[1].lap_time)
print(f"  best pressure: {best_p:.1f} bar -> {best_r.lap_time:.3f}s")
