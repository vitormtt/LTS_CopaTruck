"""
Setup optimization page component for the Streamlit UI.

Grid search optimizer over anti-roll bar stiffnesses and wing positions.

Author: Lap Time Simulator Team
Date: 2026-06-06
"""
import time
from itertools import product
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.vehicle.fleet import get_vehicle_by_id
from src.vehicle.setup import VehicleSetup, apply_setup
from .helpers import cached_solver, fmt_laptime, init_session_state


def optimization_page() -> None:
    st.header("🔧 Setup Optimization")
    init_session_state()

    if st.session_state.circuit is None:
        st.warning("⚠️ Select a track in the 'Track' tab first.")
        return

    mode = st.session_state.get("confirmed_mode") or st.session_state.get("vehicle_mode", "Copa Truck")
    if mode != "Porsche GT3 Cup":
        st.warning(
            "Setup optimization is currently only available for **Porsche GT3 Cup** mode. "
            "Go to the **Parameters** tab, select Porsche GT3 Cup, and click **Save Setup & Parameters**."
        )
        return

    st.caption(
        "Grid-search over ARB front, ARB rear, and Wing position to find the "
        "optimum setup combination for this track. Tyre pressure and brake bias are kept constant."
    )

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        pressure = st.number_input("Tyre Pressure (bar)", 1.4, 2.4, 1.8, step=0.05, key="opt_pressure")
    with col_p2:
        bias = st.slider("Brake Bias", -2.0, 0.0, -1.0, step=0.5, key="opt_bias")

    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1:
        arb_f_range = st.slider("ARB Front Range", 1, 7, (1, 7), key="opt_arb_f")
    with col_r2:
        arb_r_range = st.slider("ARB Rear Range", 1, 7, (1, 7), key="opt_arb_r")
    with col_r3:
        wing_range = st.slider("Wing Position Range", 1, 9, (1, 9), key="opt_wing")

    arb_f_vals = list(range(arb_f_range[0], arb_f_range[1] + 1))
    arb_r_vals = list(range(arb_r_range[0], arb_r_range[1] + 1))
    wing_vals = list(range(wing_range[0], wing_range[1] + 1))
    total = len(arb_f_vals) * len(arb_r_vals) * len(wing_vals)

    st.info(
        f"Total setup combinations to evaluate: **{total}** "
        f"(ARB Front: {len(arb_f_vals)} × ARB Rear: {len(arb_r_vals)} × Wing: {len(wing_vals)})"
    )

    if st.button("🚀 Run Setup Optimization Grid-Search", width="stretch", type="primary"):
        base = get_vehicle_by_id(st.session_state.vehicle_id)
        circuit = st.session_state.circuit
        results_opt = []

        bar = st.progress(0, text="Evaluating configurations...")
        t0 = time.perf_counter()

        for idx, (af, ar, w) in enumerate(product(arb_f_vals, arb_r_vals, wing_vals)):
            bar.progress(
                (idx + 1) / total,
                text=f"Combo {idx+1}/{total} — ARB {af}/{ar} | Wing {w}"
            )

            setup = VehicleSetup(
                arb_front=af,
                arb_rear=ar,
                wing_position=w,
                tyre_pressure=float(pressure),
                brake_bias=float(bias),
                setup_name=f"ARB{af}/{ar}_W{w}",
            )
            params = apply_setup(base, setup)
            params_dict = params.to_solver_dict()

            try:
                # Minimum gear 1 for Porsche GT3 Cup
                r = cached_solver(
                    params_dict=params_dict,
                    circuit=circuit,
                    config={"gear_min": 1},
                    save_csv=False
                )
                results_opt.append({
                    "arb_f": af,
                    "arb_r": ar,
                    "wing": w,
                    "lap_time": r["lap_time"],
                    "vmax_kmh": float(np.max(r["v_profile"])) * 3.6,
                    "vmean_kmh": float(np.mean(r["v_profile"])) * 3.6,
                })
            except Exception:
                results_opt.append({
                    "arb_f": af,
                    "arb_r": ar,
                    "wing": w,
                    "lap_time": float("inf"),
                    "vmax_kmh": 0.0,
                    "vmean_kmh": 0.0,
                })

        elapsed = time.perf_counter() - t0
        bar.empty()

        df_opt = pd.DataFrame(results_opt)
        valid_df = df_opt[df_opt["lap_time"] < float("inf")]
        
        if valid_df.empty:
            st.error("❌ All simulated setup configurations failed to solve.")
            return

        best = valid_df.loc[valid_df["lap_time"].idxmin()]

        st.success(
            f"✅ Grid search complete in {elapsed:.1f}s — "
            f"Optimum: **ARB {int(best.arb_f)}/{int(best.arb_r)} Wing {int(best.wing)}** "
            f"→ **{fmt_laptime(best.lap_time)}**"
        )

        # Top 10 setups
        st.subheader("🏆 Top 10 Fast Setups")
        top10 = valid_df.nsmallest(10, "lap_time").copy()
        top10["Lap Time"] = top10["lap_time"].apply(fmt_laptime)
        top10.columns = [c.replace("_", " ").title() for c in top10.columns]
        st.dataframe(top10, width="stretch")

        # Heatmaps — one per wing position
        st.subheader("🗺️ Lap-Time Sensitivity (ARB Front vs ARB Rear)")
        for w in wing_vals:
            sub = valid_df[valid_df["wing"] == w]
            if sub.empty:
                continue
            pivot = sub.pivot(index="arb_r", columns="arb_f", values="lap_time")
            
            fig_hm = go.Figure(go.Heatmap(
                z=pivot.values,
                x=[str(c) for c in pivot.columns],
                y=[str(r) for r in pivot.index],
                colorscale='RdYlGn_r',
                colorbar=dict(title='Lap (s)'),
                text=[[fmt_laptime(v) for v in row] for row in pivot.values],
                texttemplate="%{text}",
            ))
            fig_hm.update_layout(
                title=f'Wing Position = {w}',
                xaxis_title='ARB Front (Stiffness Level)',
                yaxis_title='ARB Rear (Stiffness Level)',
                height=350,
                margin=dict(l=0, r=0, t=40, b=0),
            )
            st.plotly_chart(fig_hm, width="stretch")
