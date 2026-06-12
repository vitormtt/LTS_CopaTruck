"""
Batch run simulation page component for the Streamlit UI.

Allows consecutive simulation of multiple vehicles and comparing their KPIs.

Author: Lap Time Simulator Team
Date: 2026-06-10
"""
import time
import numpy as np
import pandas as pd
import streamlit as st

from src.vehicle.fleet import list_vehicles, get_vehicle_by_id
from .helpers import init_session_state, cached_solver, fmt_laptime


def batch_run_page() -> None:
    st.header("📊 Batch Simulation")
    init_session_state()

    if st.session_state.circuit is None:
        st.warning("⚠️ Select a track in the 'Track' tab first.")
        return

    st.caption(
        "Select multiple vehicles to run consecutive simulations on the loaded track. "
        "The comparison table and summary statistics will be generated automatically."
    )

    st.info(f"✓ Track Loaded: **{st.session_state.circuit_meta['name']}**")

    # 1. Multi-vehicle selection
    all_vehicles = list_vehicles()
    selected_vids = []
    
    st.subheader("1. Select Vehicles to Simulate")
    col1, col2 = st.columns(2)
    
    vehicle_ids = list(all_vehicles.keys())
    half = (len(vehicle_ids) + 1) // 2
    
    with col1:
        for vid in vehicle_ids[:half]:
            if st.checkbox(all_vehicles[vid], value=True, key=f"batch_ch_{vid}"):
                selected_vids.append(vid)
    with col2:
        for vid in vehicle_ids[half:]:
            if st.checkbox(all_vehicles[vid], value=True, key=f"batch_ch_{vid}"):
                selected_vids.append(vid)

    # 2. Simulation Mode
    st.subheader("2. Simulation Mode")
    sim_mode = st.radio(
        "Select Mode:",
        ["Qualifying (Flying Lap)", "Standing Start (Race Start)"],
        horizontal=True
    )

    if len(selected_vids) == 0:
        st.warning("⚠️ Please select at least one vehicle.")
        return

    force_rerun = st.checkbox(
        "Force re-run (ignore solver cache)", value=False, key="batch_force_rerun",
        help="Identical vehicle+track+mode combinations are served from an "
             "in-memory cache (instant). Tick to recompute everything."
    )

    st.markdown("---")

    if st.button("🚀 Run Batch Simulation", width="stretch", type="primary"):
        results_list = []
        progress_bar = st.progress(0, text="Initializing simulations...")

        t_start = time.perf_counter()

        for idx, vid in enumerate(selected_vids):
            vp = get_vehicle_by_id(vid)
            params_dict = vp.to_solver_dict()
            params_dict.setdefault("track_width", 2.5)

            # Track grip multiplier scales the tyre friction coefficient
            grip_mult = float(getattr(st.session_state.circuit, "grip_multiplier", 1.0))

            # Formulate solver configuration
            mode_key = "standing_start" if "Standing Start" in sim_mode else "qualifying"
            solver_config = {
                "mode": mode_key,
                "coef_aderencia": vp.tire.friction_coefficient * grip_mult,
            }
            if mode_key == "standing_start":
                solver_config["launch_rpm"] = 1500.0  # diesel truck launch
                solver_config["wheelspin_limit"] = 0.15

            try:
                t0 = time.perf_counter()
                r = cached_solver(
                    params_dict=params_dict,
                    circuit=st.session_state.circuit,
                    config=solver_config,
                    save_csv=False,
                    use_cache=not force_rerun
                )
                dt = time.perf_counter() - t0

                results_list.append({
                    "Vehicle": all_vehicles[vid],
                    "Lap Time": r["lap_time"],
                    "Max Speed (km/h)": float(np.max(r["v_profile"])) * 3.6,
                    "Mean Speed (km/h)": float(np.mean(r["v_profile"])) * 3.6,
                    "Fuel Consumed (L)": float(r["consumo"][-1]),
                    "Final Tyre Temp (°C)": float(r["temp_pneu"][-1]),
                    "Compute Time (s)": dt,
                    "Source": "cache ⚡" if (not force_rerun and dt < 0.05) else "solver",
                })
            except Exception as e:
                st.error(f"❌ Failed to simulate {all_vehicles[vid]}: {e}")
                results_list.append({
                    "Vehicle": all_vehicles[vid],
                    "Lap Time": float("inf"),
                    "Max Speed (km/h)": 0.0,
                    "Mean Speed (km/h)": 0.0,
                    "Fuel Consumed (L)": 0.0,
                    "Final Tyre Temp (°C)": 0.0,
                    "Compute Time (s)": 0.0,
                    "Source": "failed",
                })
            progress_bar.progress(
                (idx + 1) / len(selected_vids),
                text=f"Simulated {all_vehicles[vid]} ({idx+1}/{len(selected_vids)})"
            )

        elapsed = time.perf_counter() - t_start
        progress_bar.empty()

        # Persist so the comparison survives any later rerun/interaction
        st.session_state["batch_results"] = pd.DataFrame(results_list)
        st.session_state["batch_elapsed"] = elapsed

    if st.session_state.get("batch_results") is not None:
        _render_batch_results(
            st.session_state["batch_results"],
            st.session_state.get("batch_elapsed", 0.0),
        )


def _render_batch_results(df: pd.DataFrame, elapsed: float) -> None:
    """Render the persisted batch comparison table and chart."""
    df_valid = df[df["Lap Time"] < float("inf")].copy()

    if df_valid.empty:
        st.error("❌ All simulations failed to run.")
        return

    # Format lap time display column
    df_valid["Lap Time Formatted"] = df_valid["Lap Time"].apply(fmt_laptime)

    # Display best run success
    best_row = df_valid.loc[df_valid["Lap Time"].idxmin()]
    st.success(
        f"✅ Batch simulation completed in {elapsed:.2f}s! "
        f"Winner: **{best_row['Vehicle']}** with lap time of **{best_row['Lap Time Formatted']}**."
    )

    st.subheader("📊 Performance KPI Comparison")

    # Format columns for display
    df_display = df_valid[[
        "Vehicle", "Lap Time Formatted", "Max Speed (km/h)",
        "Mean Speed (km/h)", "Fuel Consumed (L)", "Final Tyre Temp (°C)", "Source"
    ]].rename(columns={"Lap Time Formatted": "Lap Time"})

    st.dataframe(df_display.style.highlight_min(subset=["Lap Time"], color="#2c7a40"), width="stretch")

    # Bar chart comparison
    import plotly.express as px
    fig = px.bar(
        df_valid,
        x="Vehicle",
        y="Lap Time",
        color="Vehicle",
        text="Lap Time Formatted",
        title=f"Lap Time comparison on {st.session_state.circuit_meta['name']}"
    )
    fig.update_layout(yaxis_title="Lap Time (s)", showlegend=False, height=400)
    st.plotly_chart(fig, width="stretch")
