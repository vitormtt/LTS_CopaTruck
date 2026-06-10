"""
LapTimeSimulator — Streamlit Interface (Modular Router)

Run from project root:
    streamlit run src/visualization/interface.py
"""
import sys
import os
from pathlib import Path
from datetime import datetime
import numpy as np
import streamlit as st

# Ensure root directory is in python path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.visualization.components import (
    init_session_state,
    parametros_veiculo_page,
    pista_page,
    simulacao_page,
    resultados_page,
    compare_page,
    optimization_page,
    batch_run_page
)
from src.visualization.components.helpers import RESULTS_PATH, cached_solver, fmt_laptime

# Routing dictionary
PAGES = {
    "🚗 Parameters":    parametros_veiculo_page,
    "🗺️ Track":         pista_page,
    "▶️ Simulation":    simulacao_page,
    "📊 Batch Simulation": batch_run_page,
    "🏁 Results":       resultados_page,
    "📊 Compare":       compare_page,
    "🔧 Optimization":  optimization_page,
}

# App-wide layout configuration
st.set_page_config(
    page_title="LapTimeSimulator — Copa Truck / GT3",
    layout="wide",
    page_icon="🏁"
)

# Initialize Session State
init_session_state()

if "page" not in st.session_state:
    st.session_state.page = "🚗 Parameters"

# Sidebar navigation menu
st.sidebar.title("🏁 LapTimeSimulator")
st.sidebar.caption("Copa Truck | Porsche GT3 Cup")

page_list = list(PAGES.keys())
try:
    current_idx = page_list.index(st.session_state.page)
except ValueError:
    current_idx = 0

# Radio selection maps to page
selected_page = st.sidebar.radio("Navigate:", page_list, index=current_idx)
if selected_page != st.session_state.page:
    st.session_state.page = selected_page
    st.rerun()

# --- Global Play Button ---
st.sidebar.markdown("---")
st.sidebar.subheader("▶️ Global Simulation")

if st.session_state.circuit is None:
    st.sidebar.warning("⚠️ Select a track in the 'Track' tab first.")
elif st.session_state.vehicle_params is None or not st.session_state.params_saved:
    st.sidebar.warning("⚠️ Configure and save a vehicle in the 'Parameters' tab first.")
else:
    if st.sidebar.button("▶ Run Simulation", width="stretch", type="primary", key="global_sim_button"):
        with st.sidebar.spinner("🔄 Running QSS solver..."):
            vp = st.session_state.vehicle_params
            mode = st.session_state.get("confirmed_mode") or st.session_state.get("vehicle_mode", "Copa Truck")
            params_dict = vp.to_solver_dict()
            params_dict.setdefault("track_width", 2.5)

            # Set minimum gear limit based on vehicle type (Trucks don't use gears 1-3 on racing speed)
            gear_min = 1 if mode == "Porsche GT3 Cup" else 4
            solver_config = {"gear_min": gear_min}

            # Construct result filepath
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pista_nome = st.session_state.circuit_meta["name"].replace(" ", "_")[:20]
            csv_path = os.path.join(RESULTS_PATH, f"lap_{pista_nome}_{timestamp}.csv")

            try:
                result = cached_solver(
                    params_dict=params_dict,
                    circuit=st.session_state.circuit,
                    config=solver_config,
                    save_csv=True,
                    out_path=csv_path
                )

                st.session_state.resultados = result
                st.session_state.csv_path = csv_path
                st.session_state.resultados_prontos = True

                # Store for multi-setup comparisons
                label = st.session_state.setup.setup_name if st.session_state.setup else vp.name
                st.session_state.all_results.append({
                    "label": label,
                    "lap_time": result["lap_time"],
                    "vmax": float(np.max(result["v_profile"])) * 3.6,
                    "vmean": float(np.mean(result["v_profile"])) * 3.6,
                    "fuel_L": float(result["consumo"][-1]),
                    "tyre_temp": float(result["temp_pneu"][-1]),
                    "result_obj": result,
                })

                st.session_state.page = "🏁 Results"
                st.rerun()
            except Exception as exc:
                st.sidebar.error(f"Solver Error: {exc}")

# Execute selected page
PAGES[st.session_state.page]()
