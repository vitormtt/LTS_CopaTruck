"""
Track selection and visualization page for the Streamlit UI.

Author: Lap Time Simulator Team
Date: 2026-06-06
"""
import os
import plotly.graph_objects as go
import streamlit as st
from .helpers import DATA_PATH, load_hdf5, load_interlagos_real, init_session_state


def pista_page() -> None:
    st.header("🗭️ Track Selection")
    init_session_state()

    track_source = st.radio(
        "Track Source:",
        ["Interlagos (GPS real)", "HDF5 Circuit Files"],
        horizontal=True,
    )

    if track_source == "Interlagos (GPS real)":
        circuit, meta, plot_data = load_interlagos_real()
    else:
        if not os.path.isdir(DATA_PATH):
            st.warning(f"Tracks directory not found: {DATA_PATH}")
            return
        
        pistas = [f for f in os.listdir(DATA_PATH) if f.endswith('.hdf5')]
        if not pistas:
            st.warning(f"No .hdf5 track files found in {DATA_PATH}!")
            return
        
        # Determine index of cascavel.hdf5 if available to make it friendly
        default_idx = 0
        if "cascavel.hdf5" in pistas:
            default_idx = pistas.index("cascavel.hdf5")
            
        sel = st.selectbox(
            "Select HDF5 Circuit:",
            pistas,
            index=default_idx
        )
        circuit, meta, plot_data = load_hdf5(os.path.join(DATA_PATH, sel))

    st.session_state.circuit = circuit
    st.session_state.circuit_meta = meta

    # Plot track geometry
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=plot_data['x_c'], y=plot_data['y_c'],
        mode="lines", name="Centerline",
        line=dict(color="royalblue", width=2)
    ))
    fig.add_trace(go.Scatter(
        x=plot_data['left_x'], y=plot_data['left_y'],
        mode="lines", name="Left Boundary",
        line=dict(color='limegreen', dash='dot', width=1)
    ))
    fig.add_trace(go.Scatter(
        x=plot_data['right_x'], y=plot_data['right_y'],
        mode="lines", name="Right Boundary",
        line=dict(color='tomato', dash='dot', width=1)
    ))
    
    fig.update_layout(
        title=meta['name'],
        xaxis_title="x (m)",
        yaxis_title="y (m)",
        margin=dict(l=0, r=0, t=35, b=0),
        height=450
    )
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    st.plotly_chart(fig, use_container_width=True)
    
    st.success(f"✓ Circuit loaded: **{meta['name']}** | Length: **{meta['length']:.0f} m**")
