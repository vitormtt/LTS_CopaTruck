"""
Interactive torque/power curve editor for the Streamlit UI.

The curve is edited through a point table (st.data_editor) synced
with a live dual-axis Plotly chart: torque [Nm] on the left axis and
the derived power P = T * omega [kW] on the right axis. The table
supports adding/removing rows and pasting columns from spreadsheets.

True drag-editing of Plotly points is not supported by Streamlit
(st.plotly_chart never returns figure mutations to Python), so the
table-plus-live-preview pattern is used instead — no new
dependencies required.

The preview interpolates with np.interp (linear) to stay consistent
with the solver lookup (_torque_curve_interp in lap_time_solver.py),
not with the cubic interpolation used by ICEEngine.

Author: Lap Time Simulator Team
"""
from typing import List, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.vehicle.fleet import get_vehicle_by_id

_MIN_POINTS = 2


def _power_kw(rpm: np.ndarray, torque_nm: np.ndarray) -> np.ndarray:
    """Engine power [kW] from torque [Nm] and speed [rev/min]."""
    return torque_nm * rpm * 2.0 * np.pi / 60.0 / 1000.0


def _validate_curve(
    rpm: List[float],
    torque: List[float],
    rpm_idle: float,
    rpm_max: float,
) -> List[str]:
    """Return a list of validation error messages (empty if valid)."""
    errors: List[str] = []
    if len(rpm) < _MIN_POINTS:
        errors.append(f"Curve needs at least {_MIN_POINTS} points.")
        return errors
    if any(b <= a for a, b in zip(rpm, rpm[1:])):
        errors.append("RPM values must be strictly increasing.")
    if any(t < 0.0 for t in torque):
        errors.append("Torque values must be non-negative.")
    if rpm[0] < rpm_idle - 1e-9 or rpm[-1] > rpm_max + 1e-9:
        errors.append(
            f"RPM points must stay within [idle {rpm_idle:.0f}, "
            f"limit {rpm_max:.0f}] rev/min."
        )
    return errors


def render_torque_curve_editor(vp, vehicle_id: str) -> Tuple[List[float], List[float]]:
    """
    Render the torque curve editor for the given vehicle.

    Edits are validated live; the chart always reflects the last valid
    state. "Save curve" overwrites the torque map on the session-state
    VehicleParams; "Reset to model default" reloads the preset curve
    from data/vehicle_models.json.

    Args:
        vp: VehicleParams in session state (mutated on save).
        vehicle_id: Fleet id of the selected vehicle (re-keys the
            editor so edits don't leak across vehicles).

    Returns:
        Tuple (torque_curve_rpm, torque_curve_nm) currently active.
    """
    engine = vp.engine
    seed_df = pd.DataFrame({
        "RPM": [float(r) for r in engine.torque_curve_rpm],
        "Torque (Nm)": [float(t) for t in engine.torque_curve_nm],
    })

    edited = st.data_editor(
        seed_df,
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "RPM": st.column_config.NumberColumn(
                "RPM", min_value=0.0, max_value=20000.0, step=10.0, format="%.0f"
            ),
            "Torque (Nm)": st.column_config.NumberColumn(
                "Torque (Nm)", min_value=0.0, max_value=10000.0,
                step=10.0, format="%.0f"
            ),
        },
        key=f"torque_editor_{vehicle_id}",
    )

    cleaned = edited.dropna()
    rpm_pts = [float(r) for r in cleaned["RPM"].tolist()]
    trq_pts = [float(t) for t in cleaned["Torque (Nm)"].tolist()]

    errors = _validate_curve(rpm_pts, trq_pts, engine.rpm_idle, engine.rpm_max)
    if errors:
        for msg in errors:
            st.error(msg)
        # Fall back to the last valid curve for the preview/save
        rpm_pts = [float(r) for r in engine.torque_curve_rpm]
        trq_pts = [float(t) for t in engine.torque_curve_nm]

    # Live preview — linear interp, consistent with the solver lookup
    rpm_dense = np.linspace(rpm_pts[0], rpm_pts[-1], 200)
    trq_dense = np.interp(rpm_dense, rpm_pts, trq_pts)
    pwr_dense = _power_kw(rpm_dense, trq_dense)
    peak_idx = int(np.argmax(pwr_dense))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=rpm_dense, y=trq_dense, mode="lines", name="Torque",
        line=dict(color="firebrick", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=rpm_pts, y=trq_pts, mode="markers", name="Edit points",
        marker=dict(color="firebrick", size=9, symbol="circle-open"),
    ))
    fig.add_trace(go.Scatter(
        x=rpm_dense, y=pwr_dense, mode="lines", name="Power",
        line=dict(color="royalblue", width=2, dash="dash"), yaxis="y2",
    ))
    fig.add_annotation(
        x=rpm_dense[peak_idx], y=pwr_dense[peak_idx], yref="y2",
        text=f"Peak {pwr_dense[peak_idx]:.0f} kW @ {rpm_dense[peak_idx]:.0f} rpm",
        showarrow=True, arrowhead=2,
    )
    fig.update_layout(
        title="Torque & Power Curve",
        xaxis_title="Engine Speed (rev/min)",
        yaxis=dict(title="Torque (Nm)"),
        yaxis2=dict(title="Power (kW)", overlaying="y", side="right"),
        height=380,
        margin=dict(l=0, r=0, t=40, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig, width="stretch")

    col_save, col_reset = st.columns(2)
    with col_save:
        if st.button("Save Curve", width="stretch", key="torque_save",
                     disabled=bool(errors)):
            engine.torque_curve_rpm = rpm_pts
            engine.torque_curve_nm = trq_pts
            engine.max_torque = float(max(trq_pts))
            st.session_state.vehicle_params = vp
            st.success("Torque curve saved to vehicle parameters.")
    with col_reset:
        if st.button("Reset to Model Default", width="stretch",
                     key="torque_reset"):
            default_vp = get_vehicle_by_id(vehicle_id)
            engine.torque_curve_rpm = list(default_vp.engine.torque_curve_rpm)
            engine.torque_curve_nm = list(default_vp.engine.torque_curve_nm)
            st.session_state.pop(f"torque_editor_{vehicle_id}", None)
            st.rerun()

    return rpm_pts, trq_pts
