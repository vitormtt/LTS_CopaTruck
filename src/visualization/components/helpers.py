"""
Shared helper functions and configuration for Streamlit interface.

Author: Lap Time Simulator Team
Date: 2026-06-06
"""
import os
import sys
import json
import hashlib
import time
from pathlib import Path
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
import streamlit as st

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.simulation.lap_time_solver import run_bicycle_model
from src.tracks.generate_br_tracks import build_interlagos_real
from src.tracks.hdf5 import CircuitHDF5Reader

DATA_PATH = str(BASE_DIR / "tracks")
RESULTS_PATH = str(BASE_DIR / "src" / "results")
os.makedirs(RESULTS_PATH, exist_ok=True)

# Cache in-memory for the solver results to speed up slider interaction
_solver_result_cache: Dict[str, Dict[str, Any]] = {}


def fmt_laptime(s: float) -> str:
    """Format lap time float in seconds to MM:SS.mmm format."""
    return f"{int(s // 60)}:{s % 60:06.3f}"


def slugify_id(text: str) -> str:
    """Normalize free text into a storage id (lowercase snake_case)."""
    import re
    slug = re.sub(r"[^a-z0-9]+", "_", str(text).lower()).strip("_")
    return re.sub(r"_+", "_", slug)[:50]


def persist_simulation_result(
    vehicle_id: str,
    track_name: str,
    mode: str,
    setup_name: str,
    result: dict,
    csv_path: str = None,
) -> bool:
    """Aggregate KPIs from a solver result and persist them.

    Storage goes through db_manager (PostgreSQL simulation_results table,
    JSON fallback) so every run becomes part of the queryable history.
    """
    from src.database import db_manager
    from src.simulation.kpis import compute_kpis

    kpis = compute_kpis(result)
    return db_manager.save_simulation_result(
        vehicle_id=vehicle_id,
        track_id=slugify_id(track_name),
        mode=mode,
        setup_name=setup_name,
        csv_path=csv_path,
        **kpis,
    )


def _solver_cache_key(params_dict: dict, circuit: Any, config: dict) -> str:
    """Build a deterministic SHA256 hash from solver inputs for caching."""
    parts = []
    for k in sorted(params_dict.keys()):
        v = params_dict[k]
        if isinstance(v, np.ndarray):
            parts.append(f"{k}={v.tobytes().hex()[:32]}")
        elif isinstance(v, (list, tuple)):
            parts.append(f"{k}={str(v)}")
        else:
            parts.append(f"{k}={v}")
    parts.append(f"cfg={json.dumps(config, sort_keys=True)}")
    parts.append(f"cx={circuit.centerline_x.tobytes().hex()[:32]}")
    parts.append(f"cy={circuit.centerline_y.tobytes().hex()[:32]}")
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()


def _save_result_csv(result: dict, path: str) -> None:
    """Write a simulation result dictionary to standard CSV format."""
    df = pd.DataFrame({
        "Distance": result["distance"],
        "Time": result["time"],
        "Speed": result["v_profile"] * 3.6,
        "G_Long": result["a_long"] / 9.81,
        "G_Lat": result["a_lat"] / 9.81,
        "Gear": result["gear"],
        "Engine_RPM": result["rpm"],
    })
    df.to_csv(path, index=False)


def cached_solver(
    params_dict: dict,
    circuit: Any,
    config: dict,
    save_csv: bool = False,
    out_path: str = None,
    use_cache: bool = True
) -> dict:
    """Run solver with in-memory caching to avoid re-computing same setup."""
    key = _solver_cache_key(params_dict, circuit, config)
    if use_cache and key in _solver_result_cache:
        result = _solver_result_cache[key]
        if save_csv and out_path:
            _save_result_csv(result, out_path)
        return result
        
    result = run_bicycle_model(
        params_dict=params_dict,
        circuit=circuit,
        config=config,
        save_csv=save_csv,
        out_path=out_path
    )
    _solver_result_cache[key] = result
    return result


@st.cache_data
def load_hdf5(path: str, mtime: float = 0.0) -> Tuple[Any, dict, dict]:
    """Load a track from HDF5 and return projected coordinate dict for Plotly.

    Args:
        path: HDF5 file path.
        mtime: File modification time — part of the cache key so a
            rewritten file (e.g. a re-saved custom track) is reloaded.
    """
    circuit, meta = CircuitHDF5Reader(path).read_circuit()
    # Align Cartesian coordinates for plotting (y-axis inverted is customary in telemetry)
    x_c = -(circuit.centerline_y - circuit.centerline_y[0])
    y_c = circuit.centerline_x - circuit.centerline_x[0]
    left_x = -(circuit.left_boundary_y - circuit.centerline_y[0])
    left_y = circuit.left_boundary_x - circuit.centerline_x[0]
    right_x = -(circuit.right_boundary_y - circuit.centerline_y[0])
    right_y = circuit.right_boundary_x - circuit.centerline_x[0]
    
    plot_data = {
        "x_c": x_c, "y_c": y_c,
        "left_x": left_x, "left_y": left_y,
        "right_x": right_x, "right_y": right_y
    }
    return circuit, meta, plot_data


@st.cache_data
def load_interlagos_real() -> Tuple[Any, dict, dict]:
    """Build Interlagos real track profile and return plotting coordinate dict."""
    return load_hdf5(os.path.join(DATA_PATH, "interlagos.hdf5"))


def init_session_state() -> None:
    """Initialize standard Streamlit session state properties."""
    defaults = {
        "vehicle_mode": "Copa Truck",
        "confirmed_mode": None,
        "vehicle_id": "volkswagen_31320", # VW como padrão Copa Truck
        "vehicle_params": None,
        "solver_dict": None,
        "setup": None,
        "circuit": None,
        "circuit_meta": None,
        "resultados_prontos": False,
        "resultados": None,
        "csv_path": None,
        "all_results": [],
        "params_saved": False,
        "track_width_scale": 1.0,
        "saved_track_width_scale": 1.0,
        "track_grip_mult": 1.0,
        "saved_track_grip_mult": 1.0,
        "track_dirty": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
