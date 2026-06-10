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
    st.header("🗺️ Track Selection & Configuration")
    init_session_state()

    track_source = st.radio(
        "Track Source:",
        ["Interlagos (TUM FTM)", "HDF5 Circuit Files"],
        horizontal=True,
    )

    if track_source == "Interlagos (TUM FTM)":
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

    st.markdown("---")
    st.subheader("🔧 Edit Track Geometry & Friction")

    col_edit1, col_edit2 = st.columns(2)
    with col_edit1:
        st.session_state.track_width_scale = st.slider(
            "Track Width Scale (multiplier):",
            0.5, 2.0, st.session_state.saved_track_width_scale, 0.05
        )
    with col_edit2:
        st.session_state.track_grip_mult = st.slider(
            "Track Grip Multiplier (surface friction scale):",
            0.5, 1.5, st.session_state.saved_track_grip_mult, 0.05
        )

    # Detect unsaved changes
    if (st.session_state.track_width_scale != st.session_state.saved_track_width_scale or
            st.session_state.track_grip_mult != st.session_state.saved_track_grip_mult):
        st.session_state.track_dirty = True
        st.warning("⚠️ Alterações não salvas na pista! Clique em 'Salvar' para aplicar na simulação.")
        
        if st.button("💾 Salvar Alterações da Pista", type="primary"):
            st.session_state.saved_track_width_scale = st.session_state.track_width_scale
            st.session_state.saved_track_grip_mult = st.session_state.track_grip_mult
            st.session_state.track_dirty = False
            st.success("✓ Configuração de pista salva com sucesso!")
            st.rerun()
    else:
        st.session_state.track_dirty = False
        st.info("ℹ️ Configuração da pista salva e ativa para simulação.")

    # Apply saved modifications to the active circuit object
    w_scale = st.session_state.saved_track_width_scale
    g_mult = st.session_state.saved_track_grip_mult
    
    # Clone arrays to avoid modifying cached data directly
    circuit_c = CircuitData(
        name=meta['name'],
        centerline_x=circuit.centerline_x.copy(),
        centerline_y=circuit.centerline_y.copy(),
        left_boundary_x=circuit.left_boundary_x.copy(),
        left_boundary_y=circuit.left_boundary_y.copy(),
        right_boundary_x=circuit.right_boundary_x.copy(),
        right_boundary_y=circuit.right_boundary_y.copy(),
        track_width=circuit.track_width.copy(),
        coordinate_system=circuit.coordinate_system
    )
    
    # Scale width and recalculate boundaries if modified
    if w_scale != 1.0:
        circuit_c.track_width = circuit_c.track_width * w_scale
        dx = np.gradient(circuit_c.centerline_x)
        dy = np.gradient(circuit_c.centerline_y)
        norm = np.sqrt(dx**2 + dy**2) + 1e-12
        nx = -dy / norm
        ny = dx / norm
        hw = circuit_c.track_width / 2.0
        circuit_c.left_boundary_x = circuit_c.centerline_x + nx * hw
        circuit_c.left_boundary_y = circuit_c.centerline_y + ny * hw
        circuit_c.right_boundary_x = circuit_c.centerline_x - nx * hw
        circuit_c.right_boundary_y = circuit_c.centerline_y - ny * hw
        
        # Update plot data dynamically
        plot_data = {
            "x_c": -(circuit_c.centerline_y - circuit_c.centerline_y[0]) if track_source != "Interlagos (TUM FTM)" else circuit_c.centerline_x,
            "y_c": (circuit_c.centerline_x - circuit_c.centerline_x[0]) if track_source != "Interlagos (TUM FTM)" else circuit_c.centerline_y,
            "left_x": -(circuit_c.left_boundary_y - circuit_c.centerline_y[0]) if track_source != "Interlagos (TUM FTM)" else circuit_c.left_boundary_x,
            "left_y": (circuit_c.left_boundary_x - circuit_c.centerline_x[0]) if track_source != "Interlagos (TUM FTM)" else circuit_c.left_boundary_y,
            "right_x": -(circuit_c.right_boundary_y - circuit_c.centerline_y[0]) if track_source != "Interlagos (TUM FTM)" else circuit_c.right_boundary_x,
            "right_y": (circuit_c.right_boundary_x - circuit_c.centerline_x[0]) if track_source != "Interlagos (TUM FTM)" else circuit_c.right_boundary_y,
        }

    # Store the configured grip multiplier
    circuit_c.grip_multiplier = g_mult

    st.session_state.circuit = circuit_c
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
    st.plotly_chart(fig, width="stretch")
    
    st.success(f"✓ Circuit loaded: **{meta['name']}** | Length: **{meta['length']:.0f} m** | Grip factor: **{g_mult:.2f}x**")
