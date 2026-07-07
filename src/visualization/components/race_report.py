"""
Race Report page — Telios-style session analysis on REAL .xrk data.

Sections (all computed from logged channels, nothing fabricated):
1. Laptimes per run (validity-filtered) — consistency table
2. KPI summary of the best lap, side-by-side with the current sim lap
3. Polar grip factors (radar) — real best lap vs sim
4. Sector delta distribution vs session best (box/violin, S1..S3)
5. G-G envelope colored by speed
6. Best-lap overview: speed / brake pressure / throttle / RPM

Not available with the current Copa Truck loggers (flagged, not faked):
damper histograms (no damper pots), tyre pressures per corner (no TPMS),
pitch-vs-Ax (only PitchRate logged).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.analysis.race_report import (
    GripFactors,
    extract_session,
    grip_factors,
    lap_kpis,
    sector_deltas,
)
from src.visualization.components.helpers import fmt_laptime
from src.visualization.components.overlay import _bundled_reference_laps
from src.visualization.theme import (
    ACCENT, LATERAL, NEGATIVE, NEUTRAL, POSITIVE, REFERENCE, SEQUENTIAL, style,
)


@st.cache_data(show_spinner="Extracting .xrk session (all laps)...")
def _session(path: str, mtime: float):
    """Cached session extraction keyed by path+mtime."""
    return extract_session(path)


def _sim_lap_df() -> pd.DataFrame | None:
    """Current sim result as a lap DataFrame with canonical channels."""
    res = st.session_state.get("resultados")
    if res is None:
        return None
    g = 9.81
    return pd.DataFrame({
        "distance_m": np.asarray(res["distance"], dtype=float),
        "v_kmh": np.asarray(res["v_profile"], dtype=float) * 3.6,
        "ax_long_g": np.asarray(res["a_long"], dtype=float) / g,
        "ay_lat_g": np.asarray(res["a_lat"], dtype=float) / g,
    })


def _radar(gf_real: GripFactors, gf_sim: GripFactors | None) -> go.Figure:
    cats = ["Braking", "Cornering", "Acceleration", "Overall"]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=[gf_real.braking_g, gf_real.cornering_g, gf_real.accel_g,
           gf_real.overall_g, gf_real.braking_g],
        theta=cats + [cats[0]], name="Real (best lap)",
        line=dict(color=REFERENCE, width=2), fill="toself",
        fillcolor="rgba(154,160,173,0.15)",
    ))
    if gf_sim is not None:
        fig.add_trace(go.Scatterpolar(
            r=[gf_sim.braking_g, gf_sim.cornering_g, gf_sim.accel_g,
               gf_sim.overall_g, gf_sim.braking_g],
            theta=cats + [cats[0]], name="Sim (last run)",
            line=dict(color=ACCENT, width=2), fill="toself",
            fillcolor="rgba(242,138,31,0.15)",
        ))
    fig.update_layout(height=420, polar=dict(
        bgcolor="rgba(0,0,0,0)",
        radialaxis=dict(gridcolor="rgba(150,160,175,0.2)"),
        angularaxis=dict(gridcolor="rgba(150,160,175,0.2)"),
    ))
    return fig


def race_report_page() -> None:
    """Render the Race Report page."""
    st.header("Race report")
    st.caption("Session-level analysis of real telemetry (.xrk) — Telios-style KPIs.")

    bundled = _bundled_reference_laps()
    if not bundled:
        st.warning("No bundled .xrk sessions found (_quarantine/Perez-data).")
        return
    label = st.selectbox("Session", list(bundled), key="report_session")
    path = bundled[label]
    laps, times, meta = _session(str(path), path.stat().st_mtime)
    if not laps:
        st.error("No valid laps in this session.")
        return

    st.caption(
        f"Driver **{meta.get('Driver', '?')}** · vehicle "
        f"{meta.get('Vehicle', '?')} · venue {meta.get('Venue', '?')} · "
        f"{len(laps)} valid laps"
    )

    best_i = int(np.argmin(times))
    best_lap, best_time = laps[best_i], times[best_i]
    sim_df = _sim_lap_df()

    # --- 1. Laptimes per run ---
    st.subheader("Laptimes")
    lt = pd.DataFrame({
        "Lap": range(1, len(times) + 1),
        "Time": [fmt_laptime(t) for t in times],
        "Delta to best (s)": [round(t - best_time, 3) for t in times],
        "Top speed (km/h)": [round(float(lap["v_kmh"].max()), 1) for lap in laps],
    })
    st.dataframe(lt, width="stretch", hide_index=True)

    # --- 2. KPI summary best lap vs sim ---
    st.subheader("Best lap KPIs — real vs sim")
    k_real = lap_kpis(best_lap, best_time)
    cols = st.columns(4)
    cols[0].metric("Best lap (real)", fmt_laptime(k_real["lap_time_s"]))
    cols[1].metric("Top speed (real)", f"{k_real['top_speed_kmh']:.1f} km/h")
    cols[2].metric("Mean AyMax (real)", f"{k_real.get('mean_ay_max_g', 0):.2f} G")
    fuel_txt = (f"{k_real['fuel_l']:.1f}" if "fuel_l" in k_real else "n/a")
    cols[3].metric("Δ fuel channel (raw)", fuel_txt,
                   help="Raw 'Combustivel' channel drop over the lap — "
                        "sensor units not yet confirmed, treat as relative.")
    if sim_df is not None:
        res = st.session_state.resultados
        k_sim = lap_kpis(sim_df, float(res["lap_time"]))
        cols = st.columns(4)
        cols[0].metric("Sim lap", fmt_laptime(k_sim["lap_time_s"]),
                       delta=f"{k_sim['lap_time_s'] - k_real['lap_time_s']:+.2f} s")
        cols[1].metric("Top speed (sim)", f"{k_sim['top_speed_kmh']:.1f} km/h",
                       delta=f"{k_sim['top_speed_kmh'] - k_real['top_speed_kmh']:+.1f}")
        cols[2].metric("Mean AyMax (sim)", f"{k_sim.get('mean_ay_max_g', 0):.2f} G",
                       delta=f"{k_sim.get('mean_ay_max_g', 0) - k_real.get('mean_ay_max_g', 0):+.2f}")
        cols[3].caption("Sim fuel uses the BSFC model — see Results page.")
    else:
        st.info("Run a simulation to add the sim column to every section.")

    # --- 3. Polar grip factors ---
    st.subheader("Grip factors (polar)")
    gf_real = grip_factors(best_lap)
    gf_sim = grip_factors(sim_df) if sim_df is not None else None
    st.plotly_chart(_radar(gf_real, gf_sim), width="stretch")

    # --- 4. Sector delta distribution ---
    st.subheader("Sector deltas vs session best")
    sd = sector_deltas(laps, times, n_sectors=3)
    fig_sd = go.Figure()
    for sector, color in zip(["S1", "S2", "S3"], [ACCENT, LATERAL, POSITIVE]):
        sub = sd[sd["sector"] == sector]
        fig_sd.add_trace(go.Violin(
            y=sub["delta_s"], name=sector, line_color=color,
            box_visible=True, meanline_visible=True, points="all",
        ))
    style(fig_sd, height=360, yaxis_title="Δt vs best (s)")
    st.plotly_chart(fig_sd, width="stretch")

    # --- 5. G-G envelope colored by speed ---
    st.subheader("G-G envelope (best lap, colored by speed)")
    fig_gg = go.Figure()
    fig_gg.add_trace(go.Scatter(
        x=best_lap["ay_lat_g"], y=best_lap["ax_long_g"], mode="markers",
        marker=dict(size=3, color=best_lap["v_kmh"], colorscale=SEQUENTIAL,
                    colorbar=dict(title="km/h")),
        name="Real",
    ))
    if sim_df is not None:
        fig_gg.add_trace(go.Scatter(
            x=sim_df["ay_lat_g"], y=sim_df["ax_long_g"], mode="markers",
            marker=dict(size=3, color="rgba(242,138,31,0.45)"),
            name="Sim",
        ))
    style(fig_gg, height=460, xaxis_title="Lateral G", yaxis_title="Longitudinal G")
    fig_gg.update_yaxes(scaleanchor="x", scaleratio=1)
    st.plotly_chart(fig_gg, width="stretch")

    # --- 6. Best-lap overview (real channels) ---
    st.subheader("Best-lap overview — real driver inputs")
    channels = [
        ("v_kmh", "Speed (km/h)", REFERENCE),
        ("brake_press", "Brake pressure (raw)", NEGATIVE),
        ("throttle_pct", "Throttle (Ped, raw)", POSITIVE),
        ("rpm", "RPM", LATERAL),
    ]
    for col, title, color in channels:
        if col not in best_lap:
            continue
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=best_lap["distance_m"], y=best_lap[col], name=title,
            line=dict(color=color, width=1.5),
        ))
        if sim_df is not None and col == "v_kmh":
            fig.add_trace(go.Scatter(
                x=sim_df["distance_m"], y=sim_df["v_kmh"], name="Sim",
                line=dict(color=ACCENT, width=1.5),
            ))
        style(fig, title=title, height=220, xaxis_title="distance (m)")
        st.plotly_chart(fig, width="stretch")

    st.caption(
        "Not available on the current loggers (no data, so not shown): damper "
        "velocity histograms (no damper pots), tyre pressures per corner "
        "(no TPMS), pitch-vs-Ax platform map (only PitchRate is logged)."
    )
