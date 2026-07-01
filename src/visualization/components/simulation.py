"""
Simulation execution page for the Streamlit UI.

Author: Lap Time Simulator Team
Date: 2026-06-06
"""
import os
import time
from datetime import datetime
import numpy as np
import pandas as pd
import streamlit as st
from .helpers import (
    RESULTS_PATH,
    cached_solver,
    fmt_laptime,
    init_session_state,
    persist_simulation_result,
)


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

    tab_single, tab_sweep = st.tabs(["Single Run", "Parameter Sweep (Sensitivity Analysis)"])

    with tab_single:
        sim_mode_label = st.radio(
            "Simulation Mode:",
            ["Qualifying", "Standing Start"],
            horizontal=True,
            key="sim_mode_select",
        )
        sim_mode_key = {
            "Qualifying": "qualifying",
            "Standing Start": "standing_start",
        }[sim_mode_label]

        ambient_temp_c = 25.0

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

                    # Track grip multiplier scales the tyre friction coefficient
                    grip_mult = float(getattr(st.session_state.circuit,
                                              "grip_multiplier", 1.0))
                    solver_config = {
                        "mode": sim_mode_key,
                        "coef_aderencia": vp.tire.friction_coefficient * grip_mult,
                    }
                    if sim_mode_key == "standing_start":
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

                        # Persist the run so the history can cross-reference it
                        saved = persist_simulation_result(
                            vehicle_id=st.session_state.vehicle_id,
                            track_name=st.session_state.circuit_meta["name"],
                            mode=sim_mode_key,
                            setup_name=label,
                            result=result,
                            csv_path=csv_path,
                        )

                        st.success(
                            f"✓ Lap Completed: **{fmt_laptime(result['lap_time'])}** — "
                            f"Vmax: **{float(np.max(result['v_profile'])*3.6):.1f} km/h** — "
                            f"Compute time: {elapsed:.3f}s"
                            + (" — saved to history 🗄️" if saved else "")
                        )
                    except Exception as exc:
                        import traceback
                        st.error(f"Solver Error: {exc}")
                        st.code(traceback.format_exc())

    with tab_sweep:
        st.subheader("🛠️ Setup Parameter Sweep")
        st.write("Run multiple simulations to visualize the impact of parameter changes on lap time using Parallel Coordinates.")
        
        sim_mode_sweep = st.radio(
            "Sweep Simulation Mode:",
            ["Qualifying", "Standing Start"],
            horizontal=True,
            key="sim_mode_sweep_select",
        )
        sim_mode_sweep_key = {
            "Qualifying": "qualifying",
            "Standing Start": "standing_start",
        }[sim_mode_sweep]

        col_sw1, col_sw2 = st.columns(2)
        with col_sw1:
            cg_height_range = st.slider("CG Height Range (h_cg) [m]", 0.8, 1.5, (1.0, 1.2), 0.1)
        with col_sw2:
            aero_balance_range = st.slider("Aero Balance Range (CoP) [% Front]", 30, 70, (40, 60), 5)
            
        if st.button("▶ Run Batch Sweep", type="primary", use_container_width=True):
            with st.spinner("🔄 Running Grid Search..."):
                import itertools
                sweep_results = []
                
                cg_vals = np.arange(cg_height_range[0], cg_height_range[1] + 0.05, 0.1)
                ab_vals = np.arange(aero_balance_range[0], aero_balance_range[1] + 2.5, 5)
                
                grid = list(itertools.product(cg_vals, ab_vals))
                progress_bar = st.progress(0)
                
                grip_mult = float(getattr(st.session_state.circuit, "grip_multiplier", 1.0))
                
                for idx, (cg, ab) in enumerate(grid):
                    params_dict = vp.to_solver_dict()
                    params_dict["h_cg"] = float(cg)
                    params_dict["aero_balance"] = float(ab) / 100.0
                    params_dict.setdefault("track_width", 2.5)
                    
                    solver_config = {
                        "mode": sim_mode_sweep_key,
                        "coef_aderencia": vp.tire.friction_coefficient * grip_mult,
                    }
                    if sim_mode_sweep_key == "standing_start":
                        solver_config["launch_rpm"] = 1500.0
                    
                    try:
                        result = cached_solver(
                            params_dict=params_dict,
                            circuit=st.session_state.circuit,
                            config=solver_config,
                            save_csv=False,
                            out_path=""
                        )
                        sweep_results.append({
                            "CG Height": float(cg),
                            "Aero Balance": float(ab),
                            "Lap Time": result["lap_time"],
                            "Max Speed": float(np.max(result["v_profile"])) * 3.6,
                            "Max Lat G": float(np.max(np.abs(result["a_lat"]))) / 9.81
                        })
                    except Exception as e:
                        st.error(f"Failed run CG={cg}, AB={ab}: {e}")
                    
                    progress_bar.progress((idx + 1) / len(grid))
                
                if sweep_results:
                    st.session_state.sweep_results_df = pd.DataFrame(sweep_results)
                    st.success(f"✓ Sweep completed ({len(sweep_results)} runs). Check the 'Results' tab for the Parallel Coordinates Plot!")
