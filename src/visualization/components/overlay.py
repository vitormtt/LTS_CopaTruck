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

import io
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
from src.visualization.theme import ACCENT, NEGATIVE, NEUTRAL, POSITIVE, REFERENCE, style

logger = logging.getLogger(__name__)


# Extra channels (beyond speed) overlaid when the reference carries them.
_MULTI_CHANNELS = [
    ("ax_long_g", "Longitudinal G", "a_long"),
    ("ay_lat_g", "Lateral G", "a_lat"),
    ("throttle_pct", "Throttle (%)", "throttle_pct"),
    ("brake_pct", "Brake (%)", "brake_pct"),
]


@st.cache_data(show_spinner="Parsing .xrk session...")
def _xrk_lap_reference(
    file_bytes: bytes, lap_num: int | None
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Extract one lap of an .xrk session.

    Args:
        file_bytes: Raw .xrk upload content.
        lap_num: Lap to extract; None = fastest valid lap.

    Returns:
        (speed reference [distance_m, v_kmh], full-channel DataFrame,
        conversion metadata).
    """
    from src.tracks.telemetry_converter import convert_xrk_to_csv

    with tempfile.TemporaryDirectory() as tmp:
        xrk_path = Path(tmp) / "session.xrk"
        xrk_path.write_bytes(file_bytes)
        csv_path = Path(tmp) / "lap.csv"
        meta = convert_xrk_to_csv(str(xrk_path), str(csv_path), lap_num)
        ref = load_reference_csv(str(csv_path))
        full = pd.read_csv(csv_path).rename(columns={"distance": "distance_m"})
    return ref, full, meta


@st.cache_data(show_spinner="Reading lap list...")
def _xrk_laps(file_bytes: bytes) -> pd.DataFrame:
    """List laps (num, duration_s) of an .xrk session upload."""
    from src.tracks.telemetry_converter import list_laps

    with tempfile.TemporaryDirectory() as tmp:
        xrk_path = Path(tmp) / "session.xrk"
        xrk_path.write_bytes(file_bytes)
        return list_laps(str(xrk_path))


# Bundled real Copa Truck reference laps (gitignored telemetry). Optional:
# absent on a fresh clone, so the picker degrades to upload-only.
_BUNDLED_LAPS_DIR = (
    Path(__file__).resolve().parents[3] / "_quarantine" / "Perez-data"
)


def _bundled_reference_laps() -> dict[str, Path]:
    """Map display label -> path for bundled .xrk reference laps."""
    if not _BUNDLED_LAPS_DIR.is_dir():
        return {}
    return {p.name: p for p in sorted(_BUNDLED_LAPS_DIR.glob("*.xrk"))}


def _resolve_reference() -> tuple[str, bytes] | None:
    """Pick a reference lap source (bundled real lap or manual upload).

    Returns:
        (filename, file bytes) or None if nothing is selected yet.
    """
    bundled = _bundled_reference_laps()
    options = ["Upload a file"]
    if bundled:
        options = ["Bundled real lap", "Upload a file"]
    source = st.radio("Reference source", options, horizontal=True,
                      key="overlay_source")

    if source == "Bundled real lap":
        label = st.selectbox("Real Copa Truck lap", list(bundled),
                             key="overlay_bundled")
        return label, bundled[label].read_bytes()

    uploaded = st.file_uploader(
        "Reference lap (.xrk or .csv)", type=["csv", "xrk"],
        key="overlay_ref_csv",
        help="AiM .xrk session (lap picker built-in) or CSV with "
             "distance_m/v_kmh (aliases distance, speed_kmh; multi-lap "
             "CSVs split automatically).",
    )
    if uploaded is None:
        return None
    return uploaded.name, uploaded.getvalue()


def _pick_reference_lap(
    name: str, data: bytes
) -> tuple[pd.DataFrame, pd.DataFrame | None] | None:
    """Resolve reference bytes (.xrk or CSV) into a single reference lap.

    Returns:
        (speed reference [distance_m, v_kmh], full-channel DataFrame or None)
        or None if nothing resolves. The full DataFrame powers the
        multi-channel overlay; it is None for speed-only CSV references.
    """
    if name.lower().endswith(".xrk"):
        file_bytes = data
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
        ref, full, meta = _xrk_lap_reference(file_bytes, options[chosen])
        st.caption(
            f"Session: {meta.get('driver', '?')} · {meta.get('vehicle', '?')} · "
            f"{meta.get('venue', '?')} · {meta.get('date', '?')}"
        )
        return ref, full

    # CSV path: may contain several laps concatenated (distance resets)
    ref_all = load_reference_csv(io.BytesIO(data))
    laps = split_laps(ref_all)
    if len(laps) == 1:
        return laps[0], None
    options = {
        f"Lap {i + 1} — ~{fmt_laptime(estimate_lap_time_s(lap))} "
        f"({lap['distance_m'].iloc[-1]:.0f} m)": i
        for i, lap in enumerate(laps)
    }
    default_idx = int(np.argmin([estimate_lap_time_s(lap) for lap in laps]))
    chosen = st.selectbox(f"CSV contains {len(laps)} laps — pick one",
                          list(options), index=default_idx,
                          key="overlay_csv_lap")
    return laps[options[chosen]], None


def _render_multichannel(res: dict, ref_full: pd.DataFrame) -> None:
    """Overlay sim vs real for the channels the reference carries."""
    dist_ref = ref_full["distance_m"].to_numpy(dtype=float)
    lo, hi = dist_ref.min(), dist_ref.max()
    grid = np.linspace(lo, hi, max(int((hi - lo) / 5.0), 2))
    sim_dist = np.asarray(res["distance"], dtype=float)

    g = 9.81
    sim_channels = {
        "a_long": np.asarray(res["a_long"], dtype=float) / g,
        "a_lat": np.asarray(res["a_lat"], dtype=float) / g,
        "throttle_pct": np.asarray(res.get("throttle_pct",
                                            np.zeros_like(sim_dist)), dtype=float),
        "brake_pct": np.asarray(res.get("brake_pct",
                                        np.zeros_like(sim_dist)), dtype=float),
    }

    st.subheader("Channel overlay (sim vs real)")
    for ref_col, title, sim_key in _MULTI_CHANNELS:
        if ref_col not in ref_full:
            continue
        ref_i = np.interp(grid, dist_ref, ref_full[ref_col].to_numpy(dtype=float))
        sim_i = np.interp(grid, sim_dist, sim_channels[sim_key])
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=grid, y=ref_i, name="Real",
                                 line=dict(color=REFERENCE, width=1.6)))
        fig.add_trace(go.Scatter(x=grid, y=sim_i, name="Sim",
                                 line=dict(color=ACCENT, width=1.6)))
        style(fig, title=title, height=240, xaxis_title="distance (m)")
        st.plotly_chart(fig, width="stretch")


def overlay_page() -> None:
    """Render the sim-vs-reference overlay page."""
    st.header("Telemetry overlay")
    st.caption("Compare the simulated lap against a real reference (AiM .xrk or CSV).")

    if not st.session_state.get("resultados_prontos", False):
        st.warning("Run a simulation on the Simulation page first.")
        return

    res = st.session_state.resultados

    resolved = _resolve_reference()
    if resolved is None:
        st.info("Pick a bundled real lap or upload a reference file.")
        return
    ref_name, ref_bytes = resolved

    try:
        picked = _pick_reference_lap(ref_name, ref_bytes)
        if picked is None:
            return
        ref, ref_full = picked
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
                               line=dict(color=REFERENCE, width=2)))
    fig_v.add_trace(go.Scatter(x=overlay.grid_m, y=overlay.sim_v_kmh,
                               name="Simulation",
                               line=dict(color=ACCENT, width=2)))
    style(fig_v, title="Speed vs Distance", height=340,
          xaxis_title="distance (m)", yaxis_title="km/h")
    st.plotly_chart(fig_v, width="stretch")

    col1, col2 = st.columns(2)
    with col1:
        fig_dv = go.Figure()
        fig_dv.add_trace(go.Scatter(x=overlay.grid_m, y=overlay.delta_v_kmh,
                                    name="Δv", line=dict(color=NEGATIVE,
                                                         width=2)))
        fig_dv.add_hline(y=0.0, line_dash="dash", line_color=NEUTRAL)
        style(fig_dv, title="Δ Speed (sim − ref)", height=280,
              xaxis_title="distance (m)", yaxis_title="km/h")
        st.plotly_chart(fig_dv, width="stretch")
    with col2:
        fig_dt = go.Figure()
        fig_dt.add_trace(go.Scatter(x=overlay.grid_m, y=overlay.delta_time_s,
                                    name="Δt", line=dict(color=POSITIVE,
                                                         width=2)))
        fig_dt.add_hline(y=0.0, line_dash="dash", line_color=NEUTRAL)
        style(fig_dt, title="Cumulative Δ Time (sim − ref)", height=280,
              xaxis_title="distance (m)", yaxis_title="s")
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

    # --- Multi-channel overlay (when the reference carries the channels) ---
    if ref_full is not None:
        st.markdown("---")
        _render_multichannel(res, ref_full)
