"""
Validação de tempos de volta da Copa Truck vs Simulação LTS Perez.
Compara os tempos de qualificação simulados contra os marcos de referência (Cascavel e Interlagos).

Execução:
    python src/validation/validate_laptimes_copa_truck.py
"""
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.vehicle.fleet import get_vehicle_by_id
from src.tracks.hdf5 import CircuitHDF5Reader
from src.simulation.lap_time_solver import run_bicycle_model

# Referências de pole position e limites da Copa Truck
BENCHMARKS = {
    "cascavel": {
        "track_file": "cascavel.hdf5",
        "target_pole_s": 79.505,
        "sim_expected_range_s": (69.0, 74.0),
        "target_vmax_kmh": 193.0,
    },
    "interlagos": {
        "track_file": "interlagos.hdf5",
        "target_pole_s": 123.900,
        "sim_expected_range_s": (118.0, 126.0),
        "target_vmax_kmh": 200.0,
    },
}


def run_validation() -> bool:
    print("=== Validacao de Tempos de Volta — LTS Perez (Copa Truck) ===\n")
    vp = get_vehicle_by_id("volkswagen_31320")
    if vp is None:
        print("[-] Veiculo padrao volkswagen_31320 nao encontrado.")
        return False

    params_dict = vp.to_solver_dict()
    all_ok = True

    for track_key, bmark in BENCHMARKS.items():
        # Busca pista em tracks/ ou data/tracks/
        path1 = ROOT / "tracks" / bmark["track_file"]
        path2 = ROOT / "data" / "tracks" / bmark["track_file"]
        track_path = path1 if path1.exists() else path2

        if not track_path.exists():
            print(f"[-] Pista {bmark['track_file']} nao encontrada.")
            all_ok = False
            continue

        circuit, meta = CircuitHDF5Reader(str(track_path)).read_circuit()
        res = run_bicycle_model(params_dict, circuit, {"gear_min": 4})
        lap_time = float(res["lap_time"])
        v_max = float(np.max(res["v_profile"]) * 3.6)

        low, high = bmark["sim_expected_range_s"]
        status = "OK" if (low <= lap_time <= high) else "AVISO"
        if status != "OK":
            all_ok = False

        track_name = meta.get("name", track_key) if isinstance(meta, dict) else track_key
        print(f"Circuito: {track_name}")
        print(f"  Tempo Simulado: {lap_time:.3f} s (Faixa esperada: {low:.1f}s a {high:.1f}s)")
        print(f"  Referencia Pole Real: {bmark['target_pole_s']:.3f} s")
        print(f"  Velocidade Maxima: {v_max:.1f} km/h (Limitador: {bmark['target_vmax_kmh']:.1f} km/h)")
        print(f"  Status: {status}\n")

    return all_ok


if __name__ == "__main__":
    ok = run_validation()
    sys.exit(0 if ok else 1)
