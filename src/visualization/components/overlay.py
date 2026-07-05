"""
Telemetry Overlay page — simulated lap vs real reference lap.

Accepts a reference lap as:
- AiM ``.xrk`` session (parsed via libxrk; lap picker, fastest pre-selected);
- CSV with distance/speed channels (canonical ``distance_m``/``v_kmh`` or
  aliases; multi-lap CSVs are split at distance resets with a lap picker).

All math lives in src.analysis.overlay (pure, tested); this module is
presentation only.
"""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.analysis.overlay import (
    compute_overlay,
    estimate_lap_time_s,
    load_reference_csv,
    split_laps,
)
from src.visualization.components.helpers import fmt_laptime

logger = logging.getLogger(__name__)


@st.cache_data(show_spinner="Parsing .xrk session...")
def _xrk_lap_reference(file_bytes: bytes, lap_num: int | None) -> tuple[pd.DataFrame, dict]:
    """Extract one lap of an .xrk session as a reference DataFrame.

    Args:
        file_bytes: Raw .xrk upload content.
        lap_num: Lap to extract; None = fastest valid lap.

    Returns:
        (reference DataFrame with distance_m/v_kmh, conversion metadata).
    """
    from src.tracks.telemetry_converter import convert_xrk_to_csv

    with tempfile.TemporaryDirectory() as tmp:
        xrk_path = Path(tmp) / "session.xrk"
        xrk_path.write_bytes(file_bytes)
        csv_path = Path(tmp) / "lap.csv"
        meta = convert_xrk_to_csv(str(xrk_path), str(csv_path), lap_num)
        ref = load_reference_csv(str(csv_path))
    return ref, meta


@st.cache_data(show_spinner="Reading lap list...")
def _xrk_laps(file_bytes: bytes) -> pd.DataFrame:
    """List laps (num, duration_s) of an .xrk session upload."""
    from src.tracks.telemetry_converter import list_laps

    with tempfile.TemporaryDirectory() as tmp:
        xrk_path = Path(tmp) / "session.xrk"
        xrk_path.write_bytes(file_bytes)
        return list_laps(str(xrk_path))


def _pick_reference_lap(uploaded) -> pd.DataFrame | None:
    """Resolve the uploaded file (.xrk or CSV) into a single reference lap."""
    if uploaded.name.lower().endswith(".xrk"):
        file_bytes = uploaded.getvalue()
        laps = _xrk_laps(file_bytes)
        if laps.empty:
            st.error("No laps found in this .xrk session.")
            return None
        options = {
            f"Lap {int(r.num)} — {fmt_laptime(float(r.duration_s))}": int(r.num)
            for r in laps.itertuples()
        }
        fastest_valid = laps[laps["duration_s"] > 40.0]
        default_num = int(
            (fastest_valid if not fastest_valid.empty else laps)
            .sort_values("duration_s")["num"].iloc[0]
        )
        default_idx = list(options.values()).index(default_num)
        chosen = st.selectbox("Reference lap (.xrk)", list(options),
                              index=default_idx, key="overlay_xrk_lap")
        ref, meta = _xrk_lap_reference(file_bytes, options[chosen])
        st.caption(
            f"Session: {meta.get('driver', '?')} · {meta.get('vehicle', '?')} · "
            f"{meta.get('venue', '?')} · {meta.get('date', '?')}"
        )
        return ref

    # CSV path: may contain several laps concatenated (distance resets)
    ref_all = load_reference_csv(uploaded)
    laps = split_laps(ref_all)
    if len(laps) == 1:
        return laps[0]
    options = {
        f"Lap {i + 1} — ~{fmt_laptime(estimate_lap_time_s(lap))} "
        f"({lap['distance_m'].iloc[-1]:.0f} m)": i
        for i, lap in enumerate(laps)
    }
    default_idx = int(np.argmin([estimate_lap_time_s(lap) for lap in laps]))
    chosen = st.selectbox(f"CSV contains {len(laps)} laps — pick one",
                          list(options), index=default_idx,
                          key="overlay_csv_lap")
    return laps[options[chosen]]


def overlay_page() -> None:
    """Render the sim-vs-reference overlay page."""
    st.header("Telemetry overlay")
    st.caption("Compare the simulated lap against a real reference (AiM .xrk or CSV).")

    if not st.session_state.get("resultados_prontos", False):
        st.warning("Run a simulation on the Simulation page first.")
        return

    res = st.session_state.resultados

    st.markdown(
        "Upload a reference lap: AiM **.xrk** session (lap picker built-in) "
        "or **CSV** with `distance_m`/`v_kmh` (aliases `distance`, "
        "`speed_kmh` accepted; multi-lap CSVs are split automatically)."
    )
    uploaded = st.file_uploader("Reference lap (.xrk or .csv)",
                                type=["csv", "xrk"], key="overlay_ref_csv")
    if uploaded is None:
        st.info("Waiting for a reference lap file.")
        return

    try:
        ref = _pick_reference_lap(uploaded)
        if ref is None:
            return
        overlay = compute_overlay(res["distance"], res["v_profile"] * 3.6, ref)
    except ValueError as exc:
        st.error(f"Reference file rejected: {exc}")
        return
    except (KeyError, OSError) as exc:
        logger.error("Failed to parse reference telemetry: %s", exc)
        st.error(f"Could not parse reference telemetry: {exc}")
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
