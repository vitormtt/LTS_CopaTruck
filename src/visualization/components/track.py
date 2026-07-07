"""
Track selection and visualization page for the Streamlit UI.

Author: Lap Time Simulator Team
Date: 2026-06-06
"""
import os
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from src.tracks.hdf5 import CircuitData
from src.tracks.racing_line import compute_racing_line
from .helpers import DATA_PATH, load_hdf5, init_session_state
from src.visualization.theme import ACCENT, EDGE_WHITE, NEUTRAL


def _racing_line_plot_xy(circuit, plot_data) -> tuple:
    """Racing line projected into the plot's rotated coordinate frame."""
    center = np.column_stack([circuit.centerline_x, circuit.centerline_y])
    left = np.column_stack([circuit.left_boundary_x, circuit.left_boundary_y])
    right = np.column_stack([circuit.right_boundary_x, circuit.right_boundary_y])
    closed = bool(np.hypot(*(center[0] - center[-1])) < 5.0)
    rl = compute_racing_line(center, left, right, closed=closed)
    # Same rotation load_hdf5 applies: x_plot = -(y - y0), y_plot = x - x0.
    x0, y0 = circuit.centerline_x[0], circuit.centerline_y[0]
    return -(rl.y - y0), (rl.x - x0)

# Modified tracks are persisted here — source files are never overwritten
CUSTOM_TRACKS_SUBDIR = "custom"


def pista_page() -> None:
    st.header("Track")
    st.caption("Choose a circuit and set the track grip level before running.")
    init_session_state()

    if not os.path.isdir(DATA_PATH):
        st.warning(f"Tracks directory not found: {DATA_PATH}")
        return

    # Single source of truth: HDF5 circuit files (centerline + boundaries +
    # width, self-describing). TUM FTM / GPS are import sources that are
    # converted to HDF5 offline — not a separate runtime format.
    pistas = [f for f in os.listdir(DATA_PATH) if f.endswith(".hdf5")]
    custom_dir = os.path.join(DATA_PATH, CUSTOM_TRACKS_SUBDIR)
    if os.path.isdir(custom_dir):
        pistas += [
            os.path.join(CUSTOM_TRACKS_SUBDIR, f)
            for f in os.listdir(custom_dir) if f.endswith(".hdf5")
        ]
    if not pistas:
        st.warning(f"No .hdf5 track files found in {DATA_PATH}!")
        return

    # Default to Cascavel — the trusted calibration anchor.
    default_idx = pistas.index("cascavel.hdf5") if "cascavel.hdf5" in pistas else 0
    sel = st.selectbox("Circuit (HDF5)", pistas, index=default_idx)
    sel_path = os.path.join(DATA_PATH, sel)
    circuit, meta, plot_data = load_hdf5(sel_path, os.path.getmtime(sel_path))

    st.markdown("---")
    st.subheader("Track grip")

    st.session_state.track_grip_mult = st.slider(
        "Grip multiplier (×)", 0.5, 1.5,
        st.session_state.saved_track_grip_mult, 0.05,
        help="Track grip state: scales the tyre friction coefficient at the "
             "solver boundary. 1.00 = baseline (green track). Raise for a "
             "rubbered-in, high-grip surface; lower for a cold/dirty track. "
             "Calibrate it so the sim lap matches a real reference lap.",
    )

    st.session_state.use_racing_line = st.toggle(
        "Drive the racing line", value=st.session_state.get("use_racing_line", False),
        help="Solve on the minimum-curvature racing line within the track "
             "boundaries instead of the centerline. Much closer to real "
             "(the centerline is not the fast path). Off = simple point-mass "
             "baseline (the Hase product).",
    )

    if st.session_state.track_grip_mult != st.session_state.saved_track_grip_mult:
        st.session_state.track_dirty = True
        st.warning("Unsaved grip change — click *Save* to arm it for the run.")
        if st.button("Save track changes", type="primary"):
            st.session_state.saved_track_grip_mult = st.session_state.track_grip_mult
            st.session_state.track_dirty = False
            st.success("Track configuration saved.")
            st.rerun()
    else:
        st.session_state.track_dirty = False
        st.caption("Track configuration is saved and armed for the next run.")

    g_mult = st.session_state.saved_track_grip_mult

    # Clone so the cached circuit is never mutated; attach grip multiplier.
    circuit_c = CircuitData(
        name=meta["name"],
        centerline_x=circuit.centerline_x.copy(),
        centerline_y=circuit.centerline_y.copy(),
        left_boundary_x=circuit.left_boundary_x.copy(),
        left_boundary_y=circuit.left_boundary_y.copy(),
        right_boundary_x=circuit.right_boundary_x.copy(),
        right_boundary_y=circuit.right_boundary_y.copy(),
        track_width=circuit.track_width.copy(),
        coordinate_system=circuit.coordinate_system,
    )
    circuit_c.grip_multiplier = g_mult
    st.session_state.circuit = circuit_c
    st.session_state.circuit_meta = meta

    # Plot: white track edges, dashed-orange centerline (racing reference).
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=plot_data["left_x"], y=plot_data["left_y"],
        mode="lines", name="Track edge",
        line=dict(color=EDGE_WHITE, width=1.4),
    ))
    fig.add_trace(go.Scatter(
        x=plot_data["right_x"], y=plot_data["right_y"],
        mode="lines", name="Track edge", showlegend=False,
        line=dict(color=EDGE_WHITE, width=1.4),
    ))
    fig.add_trace(go.Scatter(
        x=plot_data["x_c"], y=plot_data["y_c"],
        mode="lines", name="Centerline",
        line=dict(color=NEUTRAL, width=1.2, dash="dash"),
    ))
    if st.session_state.get("use_racing_line", False):
        rlx, rly = _racing_line_plot_xy(circuit_c, plot_data)
        fig.add_trace(go.Scatter(
            x=rlx, y=rly, mode="lines", name="Racing line",
            line=dict(color=ACCENT, width=2.0),
        ))
    fig.update_layout(title=meta["name"], xaxis_title="x (m)",
                      yaxis_title="y (m)", height=450,
                      margin=dict(l=0, r=0, t=35, b=0))
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    st.plotly_chart(fig, width="stretch")

    c1, c2, c3 = st.columns(3)
    c1.metric("Circuit", meta["name"])
    c2.metric("Length", f"{meta['length']:.0f} m")
    c3.metric("Grip factor", f"{g_mult:.2f} ×")
