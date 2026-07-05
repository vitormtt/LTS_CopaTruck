"""
Telemetry Overlay page — simulated lap vs real reference lap.

Upload a reference CSV (``distance_m``, ``v_kmh`` — output of the .xrk
converter or any telemetry export) and compare against the last
simulation: speed overlay, Δv and cumulative Δt by distance.

All math lives in src.analysis.overlay (pure, tested); this module is
presentation only.
"""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from src.analysis.overlay import compute_overlay, load_reference_csv
from src.visualization.components.helpers import fmt_laptime


def overlay_page() -> None:
    """Render the sim-vs-reference overlay page."""
    st.header("📡 Telemetry Overlay — Sim vs Real")

    if not st.session_state.get("resultados_prontos", False):
        st.warning("⚠️ Run a simulation first (Simulation tab).")
        return

    res = st.session_state.resultados

    st.markdown(
        "Upload a reference lap CSV with columns `distance_m` and `v_kmh` "
        "(.xrk laps: convert with the telemetry converter first)."
    )
    uploaded = st.file_uploader("Reference lap CSV", type=["csv"],
                                key="overlay_ref_csv")
    if uploaded is None:
        st.info("Waiting for a reference lap file.")
        return

    try:
        ref = load_reference_csv(uploaded)
        overlay = compute_overlay(res["distance"], res["v_profile"] * 3.6, ref)
    except ValueError as exc:
        st.error(f"Reference file rejected: {exc}")
        return

    # --- Scalar metrics ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sim Lap Time", fmt_laptime(res["lap_time"]))
    c2.metric("Ref Segment Time", fmt_laptime(overlay.ref_time_s))
    c3.metric("Δt End of Lap", f"{overlay.delta_time_s[-1]:+.2f} s",
              help="Positive = sim slower than reference.")
    c4.metric("Speed RMSE", f"{overlay.rmse_kmh:.1f} km/h")

    # --- Speed overlay ---
    fig_v = go.Figure()
    fig_v.add_trace(go.Scatter(x=overlay.grid_m, y=overlay.ref_v_kmh,
                               name="Reference (real)",
                               line=dict(color="silver", width=2)))
    fig_v.add_trace(go.Scatter(x=overlay.grid_m, y=overlay.sim_v_kmh,
                               name="Simulation",
                               line=dict(color="royalblue", width=2)))
    fig_v.update_layout(title="Speed vs Distance", height=340,
                        xaxis_title="distance (m)", yaxis_title="km/h",
                        margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig_v, width="stretch")

    col1, col2 = st.columns(2)
    with col1:
        fig_dv = go.Figure()
        fig_dv.add_trace(go.Scatter(x=overlay.grid_m, y=overlay.delta_v_kmh,
                                    name="Δv", line=dict(color="tomato",
                                                         width=2)))
        fig_dv.add_hline(y=0.0, line_dash="dash", line_color="gray")
        fig_dv.update_layout(title="Δ Speed (sim − ref)", height=280,
                             xaxis_title="distance (m)", yaxis_title="km/h",
                             margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_dv, width="stretch")
    with col2:
        fig_dt = go.Figure()
        fig_dt.add_trace(go.Scatter(x=overlay.grid_m, y=overlay.delta_time_s,
                                    name="Δt", line=dict(color="seagreen",
                                                         width=2)))
        fig_dt.add_hline(y=0.0, line_dash="dash", line_color="gray")
        fig_dt.update_layout(title="Cumulative Δ Time (sim − ref)",
                             height=280, xaxis_title="distance (m)",
                             yaxis_title="s",
                             margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_dt, width="stretch")

    # --- Worst sectors table ---
    st.subheader("Largest divergences")
    seg = np.array_split(np.arange(len(overlay.grid_m)), 20)
    rows = []
    for idx in seg:
        if len(idx) < 2:
            continue
        dt_seg = overlay.delta_time_s[idx[-1]] - overlay.delta_time_s[idx[0]]
        rows.append({
            "from (m)": round(float(overlay.grid_m[idx[0]])),
            "to (m)": round(float(overlay.grid_m[idx[-1]])),
            "Δt segment (s)": round(float(dt_seg), 3),
            "mean Δv (km/h)": round(float(np.mean(overlay.delta_v_kmh[idx])), 1),
        })
    rows.sort(key=lambda r: abs(r["Δt segment (s)"]), reverse=True)
    st.dataframe(rows[:5], width="stretch")
