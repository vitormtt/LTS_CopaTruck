"""
Simulation results and telemetry page for the Streamlit UI.

Includes full interactive Plotly charts, sector timing, braking zone analysis,
and a programmatic ReportLab PDF exporter with embedded Matplotlib speed traces.

Author: Lap Time Simulator Team
Date: 2026-06-06
"""
import os
import tempfile
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import streamlit as st
from datetime import datetime
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from .helpers import fmt_laptime, init_session_state
from src.analysis.driver_report import driver_report_from_result
from src.visualization.theme import (
    ACCENT, HIGHLIGHT, LATERAL, NEGATIVE, NEUTRAL, POSITIVE, REFERENCE, SEQUENTIAL,
)


# Sector/segment analysis: Brazilian circuits run 3 timing sectors; corners
# are detected where sustained lateral load exceeds the threshold below.
_N_SECTORS = 3
_CORNER_LAT_G = 0.30          # |a_lat| above this = cornering [G]
_MIN_SEGMENT_M = 30.0         # merge blips shorter than this [m]


def _lap_segments(dist, time_s, v_kmh, alat_g) -> list:
    """Split the lap into corner/straight segments from the lateral-G trace.

    Returns:
        List of dicts: label, kind ('corner'|'straight'), from_m, to_m,
        time_s, v_min, v_max, peak_lat_g.
    """
    is_corner = np.abs(alat_g) > _CORNER_LAT_G
    # Segment boundaries where the corner flag flips
    change = np.flatnonzero(np.diff(is_corner.astype(int))) + 1
    starts = np.concatenate([[0], change])
    ends = np.concatenate([change, [len(dist)]])

    raw = [(int(a), int(b), bool(is_corner[a])) for a, b in zip(starts, ends)]
    # Merge segments shorter than the blip threshold into the previous one
    merged = []
    for a, b, corner in raw:
        length = dist[b - 1] - dist[a]
        if merged and length < _MIN_SEGMENT_M:
            merged[-1] = (merged[-1][0], b, merged[-1][2])
        else:
            merged.append((a, b, corner))

    segments, n_corner, n_straight = [], 0, 0
    for a, b, corner in merged:
        sl = slice(a, b)
        if corner:
            n_corner += 1
            label = f"Turn {n_corner}"
        else:
            n_straight += 1
            label = f"Straight {n_straight}"
        segments.append({
            "label": label,
            "kind": "corner" if corner else "straight",
            "from_m": float(dist[a]),
            "to_m": float(dist[b - 1]),
            "time_s": float(time_s[b - 1] - time_s[a]),
            "v_min": float(np.min(v_kmh[sl])),
            "v_max": float(np.max(v_kmh[sl])),
            "peak_lat_g": float(np.max(np.abs(alat_g[sl]))),
        })
    return segments


def generate_pdf_report(res: dict, circuit: Any, meta: dict, vehicle_name: str, filepath: str,
                        params: dict | None = None) -> None:
    """Generate a clean PDF engineering report using ReportLab."""
    doc = SimpleDocTemplate(filepath, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []

    # 1. Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#1A365D') # Sleek navy
    )
    section_style = ParagraphStyle(
        'DocSection',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#2C5282'),
        spaceBefore=12,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14
    )
    header_style = ParagraphStyle(
        'DocHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.white
    )

    # 2. Header / Title
    story.append(Paragraph("SARU Dynamics & LTS Perez", body_style))
    story.append(Paragraph("Lap Time Simulation Report", title_style))
    story.append(Spacer(1, 10))

    # 3. Metadata block
    meta_data = [
        [Paragraph("<b>Date:</b>", body_style), Paragraph(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), body_style),
         Paragraph("<b>Track:</b>", body_style), Paragraph(meta['name'], body_style)],
        [Paragraph("<b>Vehicle:</b>", body_style), Paragraph(vehicle_name, body_style),
         Paragraph("<b>Lap Time:</b>", body_style), Paragraph(fmt_laptime(res['lap_time']), body_style)]
    ]
    t_meta = Table(meta_data, colWidths=[80, 180, 80, 200])
    t_meta.setStyle(TableStyle([
        ('LINEBELOW', (0, -1), (-1, -1), 1, colors.HexColor('#CBD5E0')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 15))

    # 4. Performance KPIs Table
    story.append(Paragraph("Performance KPIs", section_style))
    
    g = 9.81
    v_kmh = res['v_profile'] * 3.6
    alon_g = res['a_long'] / g
    alat_g = res['a_lat'] / g
    dist = res['distance']
    
    # Calculate stats
    avg_speed = float(np.mean(v_kmh))
    max_speed = float(np.max(v_kmh))
    peak_lat_g = float(np.max(np.abs(alat_g)))
    peak_brake_g = float(np.min(alon_g))
    fuel_used = float(np.max(res['consumo']))
    tyre_temp_end = float(res['temp_pneu'][-1])

    kpi_rows = [
        [Paragraph("Metric", header_style), Paragraph("Value", header_style), Paragraph("Metric", header_style), Paragraph("Value", header_style)],
        [Paragraph("Lap Time", body_style), Paragraph(fmt_laptime(res['lap_time']), body_style), Paragraph("Avg Speed", body_style), Paragraph(f"{avg_speed:.1f} km/h", body_style)],
        [Paragraph("Max Speed", body_style), Paragraph(f"{max_speed:.1f} km/h", body_style), Paragraph("Peak Lateral Acceleration", body_style), Paragraph(f"{peak_lat_g:.2f} G", body_style)],
        [Paragraph("Peak Braking Acceleration", body_style), Paragraph(f"{peak_brake_g:.2f} G", body_style), Paragraph("Fuel Consumption", body_style), Paragraph(f"{fuel_used:.3f} L", body_style)],
        [Paragraph("Final Tyre Temp", body_style), Paragraph(f"{tyre_temp_end:.1f} °C", body_style), Paragraph("Distance", body_style), Paragraph(f"{dist[-1]:.1f} m", body_style)]
    ]
    
    t_kpis = Table(kpi_rows, colWidths=[160, 110, 160, 110])
    t_kpis.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2B6CB0')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_kpis)
    story.append(Spacer(1, 15))

    # 5. Speed Trace Matplotlib Plot
    story.append(Paragraph("Speed Trace", section_style))
    
    # Render static matplotlib plot
    plt.figure(figsize=(7, 2.8))
    plt.plot(dist, v_kmh, color='#2B6CB0', linewidth=1.5)
    plt.title("Speed Trace (Distance Domain)", fontsize=10, fontweight='bold', color='#1A365D')
    plt.xlabel("Distance (m)", fontsize=8)
    plt.ylabel("Speed (km/h)", fontsize=8)
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tick_params(labelsize=8)
    plt.tight_layout()
    
    # Save to temporary file
    temp_img = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    plt.savefig(temp_img.name, dpi=150)
    plt.close()
    
    # Add image to PDF
    story.append(Image(temp_img.name, width=490, height=196))
    story.append(Spacer(1, 15))

    # 6. Sector Times
    story.append(Paragraph("Sector Timing", section_style))
    track_len = float(dist[-1])
    n_sectors = 3
    sector_boundaries = np.linspace(0, track_len, n_sectors + 1)
    
    sector_rows = [
        [Paragraph("Sector", header_style), Paragraph("From (m)", header_style), Paragraph("To (m)", header_style), Paragraph("Duration (s)", header_style), Paragraph("V avg (km/h)", header_style)]
    ]
    
    for s_idx in range(n_sectors):
        s_start, s_end = sector_boundaries[s_idx], sector_boundaries[s_idx + 1]
        mask = (dist >= s_start) & (dist < s_end)
        if not np.any(mask):
            continue
        idxs = np.where(mask)[0]
        t_sector = res['time'][idxs[-1]] - res['time'][idxs[0]]
        v_avg_s = float(np.mean(v_kmh[mask]))
        sector_rows.append([
            Paragraph(f"Sector {s_idx+1}", body_style),
            Paragraph(f"{s_start:.0f}", body_style),
            Paragraph(f"{s_end:.0f}", body_style),
            Paragraph(f"{t_sector:.3f} s", body_style),
            Paragraph(f"{v_avg_s:.1f}", body_style)
        ])
        
    t_sec = Table(sector_rows, colWidths=[100, 100, 100, 120, 120])
    t_sec.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4A5568')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_sec)

    # 7. Handling & Brake Balance (optional — needs vehicle params)
    if params is not None:
        try:
            dr = driver_report_from_result(res, params)
        except (KeyError, ValueError):
            dr = None
        if dr is not None:
            lk, bk = dr.lockup_kpis, dr.balance_kpis
            tendency = "Understeer" if bk['mean_balance'] > 0 else "Oversteer"
            story.append(Spacer(1, 15))
            story.append(Paragraph("Handling & Brake Balance", section_style))
            bal_rows = [
                [Paragraph("Metric", header_style), Paragraph("Value", header_style),
                 Paragraph("Metric", header_style), Paragraph("Value", header_style)],
                [Paragraph("Peak Front Lockup Margin", body_style), Paragraph(f"{lk['peak_front_margin']:.2f}", body_style),
                 Paragraph("Peak Rear Lockup Margin", body_style), Paragraph(f"{lk['peak_rear_margin']:.2f}", body_style)],
                [Paragraph("Near-Lockup Time", body_style), Paragraph(f"{lk['near_lockup_fraction'] * 100:.0f} %", body_style),
                 Paragraph("Understeer Time", body_style), Paragraph(f"{bk['understeer_fraction'] * 100:.0f} %", body_style)],
                [Paragraph("Mean Balance", body_style), Paragraph(f"{bk['mean_balance']:+.3f} ({tendency})", body_style),
                 Paragraph("Peak Front / Rear Util", body_style), Paragraph(f"{bk['peak_front_utilisation']:.2f} / {bk['peak_rear_utilisation']:.2f}", body_style)],
            ]
            t_bal = Table(bal_rows, colWidths=[160, 110, 160, 110])
            t_bal.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2B6CB0')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(t_bal)

    # Build document
    doc.build(story)
    
    # Cleanup temp image
    try:
        os.unlink(temp_img.name)
    except OSError:
        pass


def _render_simulation_history() -> None:
    """Persisted run history (PostgreSQL, JSON fallback) with filters.

    This is the cross-reference base: every Run/Batch simulation lands
    here, so vehicles, setups and solver iterations can be compared
    against previous results.
    """
    from src.database import db_manager
    from src.vehicle.fleet import list_vehicles

    with st.expander("Simulation history"):
        col_v, col_t, col_r = st.columns([2, 2, 1])
        fleet_names = list_vehicles()
        with col_v:
            vehicle_filter = st.selectbox(
                "Vehicle", ["(all)"] + list(fleet_names.keys()),
                format_func=lambda x: fleet_names.get(x, x), key="hist_vehicle"
            )
        with col_t:
            track_filter = st.text_input(
                "Track contains", "", key="hist_track",
                help="Filter by track id substring (e.g. cascavel)"
            )
        with col_r:
            st.write("")
            st.button("↻ Reload", key="hist_reload", width="stretch")

        rows = db_manager.list_simulation_results(
            vehicle_id=None if vehicle_filter == "(all)" else vehicle_filter
        )
        if track_filter.strip():
            rows = [r for r in rows if track_filter.strip().lower() in str(r.get("track_id", ""))]

        if not rows:
            st.info("No persisted runs yet — every Run/Batch simulation is saved here.")
            return

        hist = pd.DataFrame(rows)
        display_cols = [c for c in (
            "created_at", "vehicle_id", "track_id", "mode", "setup_name",
            "lap_time", "max_speed_kmh", "time_wot_pct", "time_braking_pct",
            "fuel_total_l", "final_tyre_temp_c",
        ) if c in hist.columns]
        hist = hist[display_cols].copy()
        if "lap_time" in hist.columns:
            best = hist["lap_time"].min()
            hist["delta_to_best"] = hist["lap_time"] - best
            hist["lap_time"] = hist["lap_time"].apply(fmt_laptime)
        st.caption(f"{len(hist)} run(s) — delta_to_best compares lap times inside this filter.")
        st.dataframe(hist, width="stretch", hide_index=True)


def resultados_page() -> None:
    st.header("Results")
    st.caption("Telemetry dashboard, KPIs and exports for the last simulated lap.")
    init_session_state()

    # --- Sweep Results (PCP) ---
    if st.session_state.get("sweep_results_df") is not None and not st.session_state.sweep_results_df.empty:
        df_sweep = st.session_state.sweep_results_df
        st.subheader("Parameter sweep — sensitivity analysis")
        st.caption("Drag the axes to filter and inspect setup trade-offs.")
        
        fig_pcp = go.Figure(data=
            go.Parcoords(
                line=dict(color=df_sweep['Lap Time'],
                          colorscale='RdYlGn_r', # Red is high (slow), Green is low (fast)
                          showscale=True,
                          cmin=df_sweep['Lap Time'].min(),
                          cmax=df_sweep['Lap Time'].max()),
                dimensions=[
                    dict(label='CG Height [m]', values=df_sweep['CG Height']),
                    dict(label='Aero Balance (CoP)', values=df_sweep['Aero Balance']),
                    dict(label='Max Lat G', values=df_sweep['Max Lat G']),
                    dict(label='Max Speed [km/h]', values=df_sweep['Max Speed']),
                    dict(label='Lap Time [s]', values=df_sweep['Lap Time'])
                ]
            )
        )
        fig_pcp.update_layout(height=400, margin=dict(l=40, r=40, t=40, b=40))
        st.plotly_chart(fig_pcp, use_container_width=True)
        st.markdown("---")

    if not st.session_state.get("resultados_prontos", False):
        st.warning("Run a simulation on the Simulation page first.")
        return

    res = st.session_state.resultados
    csv_file = st.session_state.csv_path
    circuit = st.session_state.circuit
    vp = st.session_state.vehicle_params

    g = 9.81
    v_kmh = res['v_profile'] * 3.6
    alon_g = res['a_long'] / g
    alat_g = res['a_lat'] / g
    dist = res['distance']

    tempo_total = res['time'][-1]
    dt_arr = np.diff(np.append([0], res['time']))
    time_wot = float(np.sum((alon_g > 0.05) * dt_arr))
    time_brake = float(np.sum((alon_g < -0.1) * dt_arr))
    max_lat_g = float(np.max(np.abs(alat_g)))
    # Quasi-static cabin roll derived from lateral acceleration and the
    # total roll stiffness: phi = m·ay·h_cg / (k_roll_f + k_roll_r) [rad].
    # k_roll is an uncalibrated preset value — treat magnitude as indicative.
    k_roll_total = float(vp.k_roll_front + vp.k_roll_rear)
    roll_deg = np.degrees(
        vp.mass_geometry.mass * (alat_g * g) * vp.mass_geometry.cg_height
        / max(k_roll_total, 1e-9))
    max_roll = float(np.max(np.abs(roll_deg)))
    t_pneu_fim = float(res['temp_pneu'][-1])
    p_pneu_arr = res.get('pressao_pneu', np.ones(len(dist)) * 2.0)
    p_pneu_fim = float(p_pneu_arr[-1])

    # --- KPIs Panel ---
    st.subheader("Performance KPIs")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Lap Time", fmt_laptime(res['lap_time']))
    c2.metric("Avg Speed", f"{float(np.mean(v_kmh)):.1f} km/h")
    c3.metric("Max Speed", f"{float(np.max(v_kmh)):.1f} km/h")
    c4.metric("WOT (Full Throttle)", f"{(time_wot/tempo_total)*100:.1f} %")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Peak Lateral G", f"{max_lat_g:.2f} G")
    c6.metric("Peak Braking G", f"{float(np.min(alon_g)):.2f} G")
    c7.metric("Peak Accel G", f"{float(np.max(alon_g)):.2f} G")
    c8.metric("Braking Zone Time", f"{(time_brake/tempo_total)*100:.1f} %")

    fuel_total = float(np.max(res['consumo']))
    dist_km = float(dist[-1]) / 1000.0 if len(dist) else 0.0
    fuel_per_km_out = fuel_total / dist_km if dist_km > 0 else 0.0

    c9, c10, c11, c12 = st.columns(4)
    c9.metric("Cabin Roll Angle", f"{max_roll:.2f} °")
    c10.metric("Final Tyre Temp", f"{t_pneu_fim:.1f} °C")
    c11.metric("Final Tyre Pressure", f"{p_pneu_fim:.2f} bar")
    c12.metric("Total Fuel Used", f"{fuel_total:.3f} L")

    c13, c14, _, _ = st.columns(4)
    c13.metric("Avg Consumption", f"{fuel_per_km_out:.2f} L/km",
               help="Computed dynamically from BSFC × instantaneous power.")
    c14.metric("Fuel Mass Burned", f"{fuel_total * float(getattr(vp, 'fuel_density_kg_per_l', 0.85)):.1f} kg")

    st.markdown("---")

    # --- Exporters Block ---
    st.subheader("Export deliverables")
    col_csv, col_pdf, col_html = st.columns(3)

    with col_csv:
        if csv_file and os.path.exists(csv_file):
            with open(csv_file, "rb") as f:
                st.download_button(
                    label="Telemetry CSV",
                    data=f,
                    file_name=f"Telemetry_{vp.name.replace(' ', '_')}_{datetime.now().strftime('%H%M%S')}.csv",
                    mime="text/csv",
                    width="stretch"
                )
                
    with col_pdf:
        # Generate PDF to a temporary path, then serve as download button
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
            pdf_path = tmp_pdf.name
            
        try:
            generate_pdf_report(res, circuit, st.session_state.circuit_meta, vp.name, pdf_path,
                                params=vp.to_solver_dict())
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="PDF engineering report",
                    data=f,
                    file_name=f"Report_{vp.name.replace(' ', '_')}_{datetime.now().strftime('%H%M%S')}.pdf",
                    mime="application/pdf",
                    width="stretch",
                    type="primary"
                )
            os.unlink(pdf_path)
        except Exception as pdf_err:
            st.error(f"Error compiling PDF: {pdf_err}")
            
    with col_html:
        # Placeholder / button for HTML dashboard compile
        html_export_triggered = st.button("Interactive HTML report", width="stretch")

    st.markdown("---")
    
    # --- Interactive plots (grouped into tabs) ---
    tab_dyn, tab_bf, tab_cd, tab_bal, tab_sec = st.tabs(
        ["Track & dynamics", "Brake & fuel", "Chassis & driver",
         "Balance & lockup", "Sectors"])

    with tab_dyn:
        st.subheader("Speed map")

        x_c = circuit.centerline_x
        y_c = circuit.centerline_y
        n = min(len(x_c), len(v_kmh))
    
        fig_map = go.Figure()
        fig_map.add_trace(go.Scatter(
            x=x_c[:n], y=y_c[:n], mode='markers',
            marker=dict(
                size=3,
                color=v_kmh[:n],
                colorscale='RdYlGn',
                colorbar=dict(title='Speed (km/h)'),
                cmin=float(np.min(v_kmh[:n])),
                cmax=float(np.max(v_kmh[:n])),
            ),
            name='Speed',
        ))
        fig_map.update_layout(
            xaxis_title='x — local track frame (m)',
            yaxis_title='y — local track frame (m)',
            height=500, margin=dict(l=0, r=0, t=35, b=0),
        )
        fig_map.update_yaxes(scaleanchor='x', scaleratio=1)
        st.plotly_chart(fig_map, width="stretch")

        st.markdown("---")
        st.subheader("Dynamics channels")

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            fig_v = go.Figure()
            fig_v.add_trace(go.Scatter(x=dist, y=v_kmh, mode='lines',
                                       name='Speed', line=dict(color=ACCENT, width=2)))
            fig_v.update_layout(title='Speed Trace', height=280,
                                xaxis_title='Distance (m)',
                                yaxis_title='Speed (km/h)',
                                margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_v, width="stretch")

        with col_g2:
            fig_a = go.Figure()
            fig_a.add_trace(go.Scatter(x=dist, y=alat_g, mode='lines',
                                       name='Lat G', line=dict(color=LATERAL, width=2)))
            fig_a.add_trace(go.Scatter(x=dist, y=alon_g, mode='lines',
                                       name='Long G', line=dict(color=POSITIVE, width=2)))
            fig_a.update_layout(title='Longitudinal & Lateral Accelerations', height=280,
                                xaxis_title='Distance (m)',
                                yaxis_title='Acceleration (G)',
                                margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_a, width="stretch")

        col_g3, col_g4 = st.columns(2)
        with col_g3:
            fig_temp = go.Figure()
            fig_temp.add_trace(go.Scatter(x=dist, y=res['temp_pneu'], mode='lines',
                                          name='Tyre Temp',
                                          line=dict(color=ACCENT, width=2)))
            fig_temp.add_hline(y=95.0, line_dash='dash', line_color=POSITIVE,
                               annotation_text='Optimum Target')
            fig_temp.update_layout(title='Tyre Temperature', height=280,
                                   xaxis_title='Distance (m)',
                                   yaxis_title='Temperature (°C)',
                                   margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_temp, width="stretch")

        with col_g4:
            fig_press = go.Figure()
            fig_press.add_trace(go.Scatter(x=dist, y=p_pneu_arr, mode='lines',
                                           name='Tyre Press',
                                           line=dict(color=REFERENCE, width=2)))
            fig_press.update_layout(title='Tyre Pressure', height=280,
                                    xaxis_title='Distance (m)',
                                    yaxis_title='Pressure (bar)',
                                    margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_press, width="stretch")

        col_g5, col_g6 = st.columns(2)
        with col_g5:
            # RPM on the primary axis, gear as an integer step on its own axis —
            # no more "gear ×1000" overlaid on the RPM scale.
            max_gear = int(np.max(res['gear'])) if len(res['gear']) else 1
            fig_rpm = make_subplots(specs=[[{"secondary_y": True}]])
            fig_rpm.add_trace(
                go.Scatter(x=dist, y=res['rpm'], mode='lines', name='RPM',
                           line=dict(color=HIGHLIGHT, width=2)),
                secondary_y=False,
            )
            fig_rpm.add_trace(
                go.Scatter(x=dist, y=res['gear'], mode='lines', name='Gear',
                           line=dict(color=NEUTRAL, width=1.8, shape='hv')),
                secondary_y=True,
            )
            fig_rpm.update_yaxes(title_text='RPM', secondary_y=False)
            fig_rpm.update_yaxes(title_text='Gear', secondary_y=True, showgrid=False,
                                 range=[0.5, max_gear + 0.5], dtick=1)
            fig_rpm.update_layout(title='Engine RPM + Gear', height=280,
                                  xaxis_title='Distance (m)',
                                  margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_rpm, width="stretch")

        with col_g6:
            # G-Sum Calculation for Brake Trace Analysis
            g_sum = np.sqrt(alon_g**2 + alat_g**2)
        
            fig_ggv = go.Figure()
            fig_ggv.add_trace(go.Scatter(
                x=alat_g, y=alon_g, mode='markers',
                marker=dict(size=3, color=g_sum, colorscale=SEQUENTIAL,
                            colorbar=dict(title='G-Sum')),
            ))
            fig_ggv.update_layout(
                title='GGV Diagram (Color = G-Sum Magnitude)',
                xaxis_title='Lateral acceleration (G)',
                yaxis_title='Longitudinal acceleration (G)',
                height=400, yaxis_range=[-1.5, 1.5], xaxis_range=[-1.5, 1.5],
                margin=dict(l=0, r=0, t=30, b=0),
            )
            fig_ggv.update_yaxes(scaleanchor='x', scaleratio=1)
            st.plotly_chart(fig_ggv, width="stretch")

    with tab_bf:
        # --- Brake Trace Analysis (Trail-Braking) ---
        st.subheader("Brake trace analysis")
        st.caption("G-sum transition from pure braking to pure cornering (trail-braking).")
    
        col_bt1, col_bt2 = st.columns(2)
        with col_bt1:
            fig_bt = go.Figure()
            # Only show where braking is active or transitioning (a_long < -0.1)
            fig_bt.add_trace(go.Scatter(x=dist, y=np.abs(alon_g), mode='lines',
                                        name='Long Decel (G)', line=dict(color=POSITIVE, width=2)))
            fig_bt.add_trace(go.Scatter(x=dist, y=np.abs(alat_g), mode='lines',
                                        name='Lat G (Absolute)', line=dict(color=LATERAL, width=2)))
            fig_bt.add_trace(go.Scatter(x=dist, y=g_sum, mode='lines',
                                        name='G-Sum Magnitude', line=dict(color=HIGHLIGHT, width=2, dash='dot')))
            fig_bt.update_layout(title='Braking Transition (G-Sum)', height=280,
                                 xaxis_title='Distance (m)',
                                 yaxis_title='Acceleration (G)',
                                 margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_bt, width="stretch")

        # --- Fuel consumption (dynamic BSFC model) ---
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            fig_fuel = go.Figure()
            fig_fuel.add_trace(go.Scatter(
                x=dist, y=res['consumo'], mode='lines',
                name='Fuel used', line=dict(color=ACCENT, width=2)))
            fig_fuel.update_layout(title='Cumulative Fuel Used', height=280,
                                   xaxis_title='Distance (m)',
                                   yaxis_title='Fuel used (L)',
                                   margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_fuel, width="stretch")
        with col_f2:
            # Instantaneous fuel flow [L/h] from the cumulative channel
            with np.errstate(divide='ignore', invalid='ignore'):
                fuel_flow = np.gradient(res['consumo'], res['time']) * 3600.0
            fuel_flow = np.nan_to_num(fuel_flow, nan=0.0, posinf=0.0, neginf=0.0)
            fig_flow = go.Figure()
            fig_flow.add_trace(go.Scatter(
                x=dist, y=fuel_flow, mode='lines',
                name='Fuel flow', line=dict(color=ACCENT, width=2)))
            fig_flow.update_layout(title='Fuel Flow', height=280,
                                   xaxis_title='Distance (m)',
                                   yaxis_title='Fuel flow (L/h)',
                                   margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_flow, width="stretch")



    with tab_cd:
        # --- Roll & Slip ---
        col_g7, col_g8 = st.columns(2)
        with col_g7:
            fig_roll = go.Figure()
            fig_roll.add_trace(go.Scatter(
                x=dist, y=roll_deg, mode='lines',
                name='Roll angle', line=dict(color=REFERENCE, width=2)))
            fig_roll.update_layout(title='Cabin Roll Angle', height=280,
                                   xaxis_title='Distance (m)',
                                   yaxis_title='Roll angle (deg)',
                                   margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_roll, width="stretch")
            st.caption("Quasi-static: φ = m·a_lat·h_cg / k_roll. Magnitude "
                       "indicative — k_roll preset value is unsourced.")
        with col_g8:
            slip_data = res.get('front_slip_angle_deg', np.zeros(len(dist)))
            fig_slip = go.Figure()
            fig_slip.add_trace(go.Scatter(
                x=dist, y=slip_data, mode='lines',
                name='Slip angle', line=dict(color=HIGHLIGHT, width=2)))
            fig_slip.update_layout(title='Front Slip Angle', height=280,
                                   xaxis_title='Distance (m)',
                                   yaxis_title='Slip angle (deg)',
                                   margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_slip, width="stretch")

        # --- Driver Inputs ---
        st.markdown("---")
        st.subheader("Driver inputs")

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            fig_pedals = go.Figure()
            fig_pedals.add_trace(go.Scatter(
                x=dist, y=res.get('throttle_pct', np.zeros(len(dist))),
                mode='lines', name='Throttle %',
                line=dict(color=POSITIVE, width=2)))
            fig_pedals.add_trace(go.Scatter(
                x=dist, y=res.get('brake_pct', np.zeros(len(dist))),
                mode='lines', name='Brake %',
                line=dict(color=NEGATIVE, width=2)))
            fig_pedals.update_layout(
                title='Throttle & Brake (%)', height=280,
                yaxis_title='%', xaxis_title='Distance (m)',
                margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_pedals, width="stretch")

        with col_d2:
            fig_steer = go.Figure()
            fig_steer.add_trace(go.Scatter(
                x=dist, y=res.get('steering_deg', np.zeros(len(dist))),
                mode='lines', name='Steering',
                line=dict(color=LATERAL, width=2)))
            fig_steer.update_layout(
                title='Steering Angle (°)', height=280,
                yaxis_title='deg', xaxis_title='Distance (m)',
                margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_steer, width="stretch")

    with tab_bal:
        st.markdown("---")
        st.subheader("Brake lockup & handling balance")
        st.caption(
            "Derived no-ABS lockup risk and under/oversteer balance. "
            "Diagnostic only — does not change lap time.")
        try:
            dr = driver_report_from_result(res, vp.to_solver_dict())
        except (KeyError, ValueError) as exc:
            st.info(f"Driver channels unavailable for this run: {exc}")
        else:
            lu, hb = dr.lockup, dr.balance
            lk, bk = dr.lockup_kpis, dr.balance_kpis

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Peak front margin", f"{lk['peak_front_margin']:.2f}")
            m2.metric("Peak rear margin", f"{lk['peak_rear_margin']:.2f}")
            m3.metric("Near-lockup time", f"{lk['near_lockup_fraction'] * 100:.0f}%")
            mean_bal = bk['mean_balance']
            tendency = "understeer" if mean_bal > 0 else "oversteer"
            m4.metric("Mean balance", f"{mean_bal:+.3f}", tendency, delta_color="off")

            col_lock, col_bal = st.columns(2)
            with col_lock:
                fig_lock = go.Figure()
                fig_lock.add_trace(go.Scatter(
                    x=dist, y=lu.front_margin, mode='lines',
                    name='Front', line=dict(color=ACCENT, width=2)))
                fig_lock.add_trace(go.Scatter(
                    x=dist, y=lu.rear_margin, mode='lines',
                    name='Rear', line=dict(color=LATERAL, width=2)))
                fig_lock.add_hline(y=1.0, line=dict(color=NEGATIVE, width=1, dash='dash'),
                                   annotation_text='lock')
                fig_lock.update_layout(
                    title='Brake lockup margin (1.0 = lock)', height=300,
                    yaxis_title='margin', xaxis_title='Distance (m)',
                    margin=dict(l=0, r=0, t=30, b=0))
                st.plotly_chart(fig_lock, width="stretch")
            with col_bal:
                fig_bal = go.Figure()
                fig_bal.add_trace(go.Scatter(
                    x=dist, y=hb.balance, mode='lines',
                    name='Balance', line=dict(color=HIGHLIGHT, width=2)))
                fig_bal.add_hline(y=0.0, line=dict(color=NEUTRAL, width=1))
                fig_bal.add_annotation(xref='paper', yref='paper', x=0.02, y=0.98,
                                       text='understeer', showarrow=False,
                                       font=dict(color=REFERENCE, size=11))
                fig_bal.add_annotation(xref='paper', yref='paper', x=0.02, y=0.02,
                                       text='oversteer', showarrow=False,
                                       font=dict(color=REFERENCE, size=11))
                fig_bal.update_layout(
                    title='Handling balance (>0 understeer)', height=300,
                    yaxis_title='util_f − util_r', xaxis_title='Distance (m)',
                    margin=dict(l=0, r=0, t=30, b=0))
                st.plotly_chart(fig_bal, width="stretch")

    with tab_sec:
        # Sector Timing Tab
        st.markdown("---")
        st.subheader("Sector timing")
        st.caption(
            "Three sectors (equal thirds — official split marks not yet "
            "surveyed). Expand a sector to break it into corners and "
            "straights with per-segment times.")
        track_len = float(dist[-1])
        sector_boundaries = np.linspace(0, track_len, _N_SECTORS + 1)
        segments = _lap_segments(dist, res['time'], v_kmh, alat_g)

        sector_rows = []
        for s_idx in range(_N_SECTORS):
            s_start, s_end = sector_boundaries[s_idx], sector_boundaries[s_idx + 1]
            mask = (dist >= s_start) & (dist < s_end)
            if not np.any(mask):
                continue
            idxs = np.where(mask)[0]
            t_sector = res['time'][idxs[-1]] - res['time'][idxs[0]]
            sector_rows.append({
                "Sector": f"S{s_idx + 1}",
                "From (m)": f"{s_start:.0f}",
                "To (m)": f"{s_end:.0f}",
                "Time": fmt_laptime(t_sector),
                "Share (%)": f"{t_sector / tempo_total * 100.0:.1f}",
                "V avg (km/h)": f"{float(np.mean(v_kmh[mask])):.1f}",
                "V min (km/h)": f"{float(np.min(v_kmh[mask])):.1f}",
                "V max (km/h)": f"{float(np.max(v_kmh[mask])):.1f}",
            })
        if sector_rows:
            st.dataframe(pd.DataFrame(sector_rows), width="stretch",
                         hide_index=True)

        for s_idx in range(_N_SECTORS):
            s_start, s_end = sector_boundaries[s_idx], sector_boundaries[s_idx + 1]
            segs = [sg for sg in segments
                    if s_start <= (sg["from_m"] + sg["to_m"]) / 2.0 < s_end]
            if not segs:
                continue
            n_c = sum(1 for sg in segs if sg["kind"] == "corner")
            with st.expander(
                    f"S{s_idx + 1} breakdown — {n_c} corners, "
                    f"{len(segs) - n_c} straights"):
                seg_rows = [{
                    "Segment": sg["label"],
                    "From (m)": f"{sg['from_m']:.0f}",
                    "Length (m)": f"{sg['to_m'] - sg['from_m']:.0f}",
                    "Time (s)": f"{sg['time_s']:.3f}",
                    "Δ share (%)": f"{sg['time_s'] / tempo_total * 100.0:.1f}",
                    "V min (km/h)": f"{sg['v_min']:.1f}",
                    "V max (km/h)": f"{sg['v_max']:.1f}",
                    "Peak lat (G)": f"{sg['peak_lat_g']:.2f}",
                } for sg in segs]
                st.dataframe(pd.DataFrame(seg_rows), width="stretch",
                             hide_index=True)

    # Compile HTML report if requested
    if html_export_triggered:
        figs_html = [fig_map, fig_v, fig_a, fig_temp, fig_press, fig_rpm, fig_ggv]
        fig_names = ["Speed Map", "Speed", "Long & Lat G", "Tyre Temp", "Tyre Pressure", "RPM & Gear", "GGV Diagram"]
        html_parts = [
            "<html><head><meta charset='utf-8'><title>Interactive Telemetry Report</title></head><body>",
            f"<h1>LapTimeSimulator Report — Lap Time: {fmt_laptime(res['lap_time'])}</h1>",
            f"<p>Vehicle: {vp.name} | Circuit: {st.session_state.circuit_meta['name']}</p>",
            f"<p>Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>"
        ]
        for name, fig in zip(fig_names, figs_html):
            html_parts.append(f"<h2>{name}</h2>")
            html_parts.append(pio.to_html(fig, full_html=False, include_plotlyjs='cdn'))
        html_parts.append("</body></html>")
        
        st.download_button(
            label="Download HTML report",
            data="\n".join(html_parts),
            file_name=f"Interactive_Report_{datetime.now().strftime('%H%M%S')}.html",
            mime="text/html",
            width="stretch"
        )

    st.markdown("---")
    _render_simulation_history()
