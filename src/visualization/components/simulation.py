"""
Simulation execution page for the Streamlit UI.

Author: Lap Time Simulator Team
Date: 2026-06-06
"""
import os
import time
from datetime import datetime
import numpy as np
import streamlit as st
from .helpers import RESULTS_PATH, cached_solver, fmt_laptime, init_session_state


def simulacao_page() -> None:
    st.header("▶️ Run Simulation")
    init_session_state()

    if st.session_state.circuit is None:
        st.warning("⚠️ Select a track in the 'Track' tab first.")
        return
    if st.session_state.vehicle_params is None or not st.session_state.params_saved:
        st.warning("⚠️ Configure and **save** a vehicle in the 'Parameters' tab first.")
        return

    mode = st.session_state.get("confirmed_mode") or st.session_state.get("vehicle_mode", "Copa Truck")
    vp = st.session_state.vehicle_params
    
    st.info(f"✓ Track Loaded: **{st.session_state.circuit_meta['name']}** | Vehicle Mode: **{mode}** ({vp.name})")

    sim_mode_label = st.radio(
        "Simulation Mode:",
        ["Qualifying", "Standing Start", "Thermal Braking / Endurance"],
        horizontal=True,
        key="sim_mode_select",
        help="Thermal Braking adds a brake disc heat model with "
             "temperature-dependent fade (heavy-vehicle braking stress)."
    )
    sim_mode_key = {
        "Qualifying": "qualifying",
        "Standing Start": "standing_start",
        "Thermal Braking / Endurance": "endurance_thermal",
    }[sim_mode_label]

    ambient_temp_c = 25.0
    if sim_mode_key == "endurance_thermal":
        ambient_temp_c = st.number_input(
            "Ambient Temperature (°C)", 0.0, 50.0, 25.0, step=1.0,
            key="sim_ambient_temp"
        )

    col_play, col_reset = st.columns(2)
    
    with col_reset:
        if st.button("🗑️ Clear Results History", width="stretch"):
            st.session_state.resultados_prontos = False
            st.session_state.resultados = None
            st.session_state.all_results = []
            st.rerun()

    with col_play:
        if st.button("▶ Run Simulation", width="stretch", type="primary"):
            with st.spinner("🔄 Running QSS solver (two-pass dynamic equations)..."):
                # Build solver dictionary
                params_dict = vp.to_solver_dict()
                params_dict.setdefault("track_width", 2.5)

                # Trucks don't use gears 1-3 at racing speed
                gear_min = 4
                solver_config = {"gear_min": gear_min, "mode": sim_mode_key}
                if sim_mode_key == "endurance_thermal":
                    solver_config["ambient_temp_c"] = float(ambient_temp_c)
                elif sim_mode_key == "standing_start":
                    solver_config["launch_rpm"] = 1500.0  # diesel truck launch

                # Construct result filepath
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                pista_nome = st.session_state.circuit_meta["name"].replace(" ", "_")[:20]
                csv_path = os.path.join(RESULTS_PATH, f"lap_{pista_nome}_{timestamp}.csv")

                t0 = time.perf_counter()
                try:
                    result = cached_solver(
                        params_dict=params_dict,
                        circuit=st.session_state.circuit,
                        config=solver_config,
                        save_csv=True,
                        out_path=csv_path
                    )
                    elapsed = time.perf_counter() - t0

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

                    st.success(
                        f"✓ Lap Completed: **{fmt_laptime(result['lap_time'])}** — "
                        f"Vmax: **{float(np.max(result['v_profile'])*3.6):.1f} km/h** — "
                        f"Compute time: {elapsed:.3f}s"
                    )
                except Exception as exc:
                    import traceback
                    st.error(f"Solver Error: {exc}")
                    st.code(traceback.format_exc())
