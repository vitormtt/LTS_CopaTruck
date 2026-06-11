"""
Compare page component for the Streamlit UI, allowing CSV telemetry overlays.

Author: Lap Time Simulator Team
Date: 2026-06-06
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from .helpers import init_session_state

_KNOWN_COLUMNS = {
    # Current solver CSV columns → internal key mapping
    "Distance": "distance", "Time": "time", "Speed": "speed_kmh",
    "Engine_RPM": "rpm", "Gear": "gear",
    "G_Long": "g_long", "G_Lat": "g_lat",
    "Throttle_Pos": "throttle_pct", "Brake_Press": "brake_pct",
    "Steering_Angle_deg": "steering_deg", "Roll_Angle_deg": "roll_deg",
    "Front_Slip_Angle_deg": "slip_deg",
    "Fuel_Cons_Accum_L": "fuel_l", "Tyre_Temp_C": "tyre_temp",
    "Tyre_Press_bar": "tyre_press", "Corner_Radius_m": "radius",
    # Legacy CSV columns
    "distance_m": "distance", "v_kmh": "speed_kmh",
    "a_long_ms2": "g_long", "a_lat_ms2": "g_lat",
    "time_s": "time", "temp_pneu_c": "tyre_temp", "consumo_l": "fuel_l",
    "radius_m": "radius",
}


def _parse_uploaded_csv(uploaded) -> dict | None:
    """Parse an uploaded CSV and return a normalised dict of arrays."""
    try:
        df = pd.read_csv(uploaded)
    except Exception:
        return None
    df.columns = [c.strip() for c in df.columns]
    out: dict[str, np.ndarray] = {}
    for col in df.columns:
        key = _KNOWN_COLUMNS.get(col, col.lower().replace(" ", "_"))
        out[key] = df[col].values
    return out


def compare_page() -> None:
    st.header("📊 Compare Telemetry — CSV Overlay")
    init_session_state()
    
    st.caption(
        "Upload one or more CSV or AiM (.xrk / .xrz) telemetry files (exported from the simulator, "
        "or MoTeC / PiToolbox) and overlay them against the current simulation results."
    )

    uploaded_files = st.file_uploader(
        "Upload Telemetry Files (.csv, .xrk, .xrz):",
        type=["csv", "xrk", "xrz"],
        accept_multiple_files=True,
    )

    datasets = []

    # Current simulation data (if available)
    res = st.session_state.get("resultados")
    if res is not None:
        datasets.append(("Sim (current)", {
            "distance": res["distance"],
            "speed_kmh": res["v_profile"] * 3.6,
            "g_long": res["a_long"] / 9.81,
            "g_lat": res["a_lat"] / 9.81,
            "throttle_pct": res.get("throttle_pct", np.zeros(len(res["distance"]))),
            "brake_pct": res.get("brake_pct", np.zeros(len(res["distance"]))),
            "steering_deg": res.get("steering_deg", np.zeros(len(res["distance"]))),
            "tyre_temp": res.get("temp_pneu", np.zeros(len(res["distance"]))),
        }))

    if uploaded_files:
        for uf in uploaded_files:
            if uf.name.endswith(".xrk") or uf.name.endswith(".xrz"):
                import os
                from src.visualization.components.helpers import RESULTS_PATH
                from src.tracks.telemetry_converter import convert_xrk_to_csv
                
                temp_xrk_path = os.path.join(RESULTS_PATH, f"temp_{uf.name}")
                temp_csv_path = os.path.join(RESULTS_PATH, f"temp_{uf.name}.csv")
                
                with open(temp_xrk_path, "wb") as f:
                    f.write(uf.getbuffer())
                    
                try:
                    meta = convert_xrk_to_csv(temp_xrk_path, temp_csv_path)
                    st.success(
                        f"⚡ Converted **{uf.name}** | Driver: **{meta['driver']}** | "
                        f"Venue: **{meta['venue']}** | Lap: **{meta['lap_number']}** | "
                        f"Time: **{meta['lap_time_s']:.3f}s**"
                    )
                    parsed = _parse_uploaded_csv(temp_csv_path)
                except Exception as e:
                    st.error(f"❌ Error converting **{uf.name}**: {e}")
                    parsed = None
                finally:
                    if os.path.exists(temp_xrk_path):
                        os.remove(temp_xrk_path)
                    if os.path.exists(temp_csv_path):
                        os.remove(temp_csv_path)
            else:
                parsed = _parse_uploaded_csv(uf)
                
            if parsed is None:
                st.warning(f"⚠️ Could not parse **{uf.name}**")
                continue
            datasets.append((uf.name, parsed))

    # --- Top 3 setups comparison ---
    all_runs = st.session_state.get("all_results", [])
    if len(all_runs) > 0:
        st.subheader("🏆 Top 3 Simulated Laps Comparison")
        sorted_runs = sorted(all_runs, key=lambda x: x["lap_time"])[:3]
        cols = st.columns(len(sorted_runs))
        from src.visualization.components.helpers import fmt_laptime
        
        for rank, (col, run) in enumerate(zip(cols, sorted_runs)):
            with col:
                st.markdown(f"### **#{rank + 1}** {run['label']}")
                st.metric("Lap Time", fmt_laptime(run['lap_time']))
                st.metric("Max Speed", f"{run['vmax']:.1f} km/h")
                st.metric("Mean Speed", f"{run['vmean']:.1f} km/h")
                st.metric("Fuel Burned", f"{run['fuel_L']:.2f} L")
                st.metric("Tyre Temp", f"{run['tyre_temp']:.1f} °C")
        st.markdown("---")

    if len(datasets) < 1:
        st.info("💡 Run a simulation first or upload at least one telemetry CSV/XRK file.")
        return

    colors = px.colors.qualitative.Plotly
    channel_defs = [
        ("speed_kmh", "Speed (km/h)"),
        ("g_long", "Longitudinal G"),
        ("g_lat", "Lateral G"),
        ("throttle_pct", "Throttle (%)"),
        ("brake_pct", "Brake (%)"),
        ("steering_deg", "Steering Angle (°)"),
        ("tyre_temp", "Tyre Temperature (°C)"),
    ]

    for key, title in channel_defs:
        has_data = any(key in d for _, d in datasets)
        if not has_data:
            continue
            
        fig = go.Figure()
        for idx, (name, data) in enumerate(datasets):
            if key not in data:
                continue
            x = data.get("distance", np.arange(len(data[key])))
            fig.add_trace(go.Scatter(
                x=x, y=data[key],
                mode="lines",
                name=name,
                line=dict(color=colors[idx % len(colors)], width=1.5),
            ))
            
        fig.update_layout(
            title=title,
            xaxis_title="Distance (m)",
            height=300,
            margin=dict(l=0, r=0, t=35, b=0),
            hovermode="x unified"
        )
        st.plotly_chart(fig, width="stretch")
