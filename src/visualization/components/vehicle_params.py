"""
Vehicle parameters configuration page for the Streamlit UI.

Exposes the full VehicleParams field set (mass/geometry, tires,
engine, fuel, transmission, brakes, aerodynamics) grouped in
expanders. Field-friendly units (tyre pressure in psi) are converted
exactly once at the widget boundary via src.vehicle.units.

Author: Lap Time Simulator Team
Date: 2026-06-06
"""
import numpy as np
import pandas as pd
import streamlit as st

from src.vehicle.fleet import get_vehicle_by_id, list_vehicles
from src.vehicle.units import bar_to_psi, psi_to_bar
from .helpers import init_session_state
from .torque_curve import render_torque_curve_editor

# Cold pressure UI range mapped to the safe setup window (1.4–2.4 bar)
_PRESSURE_PSI_MIN = 20.5
_PRESSURE_PSI_MAX = 34.5


def _resample_gear_ratios(ratios: list, num_gears: int) -> list:
    """Resample a gear-ratio list to a new gear count, preserving shape."""
    if len(ratios) == num_gears:
        return [float(r) for r in ratios]
    old_idx = np.linspace(0.0, 1.0, len(ratios))
    new_idx = np.linspace(0.0, 1.0, num_gears)
    return [float(r) for r in np.interp(new_idx, old_idx, ratios)]


def parametros_veiculo_page() -> None:
    st.header("🚗 Vehicle Parameters & Setup")
    init_session_state()

    all_vehicles = list_vehicles()

    category_vehicles = {
        vid: name for vid, name in all_vehicles.items()
        if "volkswagen" in vid or "scania" in vid or "volvo" in vid or "copa" in vid.lower()
    }

    if not category_vehicles:
        st.error("No Copa Truck vehicles found in the fleet registry.")
        return

    # Select vehicle model
    # Keep track of last selected vehicle in session state
    default_vid = list(category_vehicles.keys())[0]
    if st.session_state.vehicle_id not in category_vehicles:
        st.session_state.vehicle_id = default_vid

    selected_vid = st.selectbox(
        "Choose Model:",
        options=list(category_vehicles.keys()),
        format_func=lambda x: category_vehicles[x]
    )

    # If selection changed, reload params
    if selected_vid != st.session_state.vehicle_id or st.session_state.vehicle_params is None:
        st.session_state.vehicle_id = selected_vid
        st.session_state.vehicle_params = get_vehicle_by_id(selected_vid)
        st.session_state.params_saved = False
        st.session_state.setup = None

    vp = st.session_state.vehicle_params

    # Main specs metrics display
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Manufacturer", vp.manufacturer)
    with col2:
        st.metric("Year", vp.year)
    with col3:
        st.metric("Power", f"{vp.engine.max_power/1000:.0f} kW ({vp.engine.max_power*0.00135962:.0f} cv)")
    with col4:
        st.metric("Weight", f"{vp.mass_geometry.mass:.0f} kg")

    st.markdown("---")

    # ---- Mandatory initial conditions --------------------------------------
    st.subheader("🏁 Initial Conditions")
    col_p, col_f = st.columns(2)
    with col_p:
        pressure_psi = st.number_input(
            "Cold Tyre Pressure (psi)",
            _PRESSURE_PSI_MIN, _PRESSURE_PSI_MAX,
            float(np.clip(bar_to_psi(vp.tire.cold_pressure_bar),
                          _PRESSURE_PSI_MIN, _PRESSURE_PSI_MAX)),
            step=0.5, key="vp_pressure_psi",
            help="Converted internally to bar; feeds the hot-pressure "
                 "trace and the pressure-dependent grip model."
        )
        vp.tire.cold_pressure_bar = psi_to_bar(pressure_psi)
        st.caption(f"= {vp.tire.cold_pressure_bar:.2f} bar")
    with col_f:
        vp.initial_fuel_l = st.number_input(
            "Initial Fuel Load (L)", 0.0, 500.0, float(vp.initial_fuel_l),
            step=5.0, key="vp_initial_fuel",
            help="Drives the dynamic vehicle mass as fuel burns during the lap."
        )

    # ---- Parameter Customization --------------------------------------------
    st.subheader("🔧 Customize Truck Parameters")

    with st.expander("⚖️ Mass & Geometry"):
        vp.mass_geometry.mass = st.number_input(
            "Race Mass (kg)", 4950.0, 9000.0,
            max(float(vp.mass_geometry.mass), 4950.0), step=50.0, key="vp_mass"
        )
        wb = st.number_input(
            "Wheelbase (m)", 3.0, 5.5, float(vp.mass_geometry.wheelbase),
            step=0.05, key="vp_wheelbase"
        )
        wd_front = st.slider(
            "Front Static Weight Distribution (%)", 30.0, 70.0,
            float(vp.mass_geometry.weight_distribution_front * 100.0),
            step=0.5, key="vp_wd_front",
            help="Source of truth for the CG position: lf and lr are "
                 "recomputed from wheelbase and this split."
        )
        vp.mass_geometry.wheelbase = wb
        vp.mass_geometry.lr = wb * (wd_front / 100.0)
        vp.mass_geometry.lf = wb - vp.mass_geometry.lr
        st.caption(
            f"CG to front axle (lf): **{vp.mass_geometry.lf:.3f} m** | "
            f"CG to rear axle (lr): **{vp.mass_geometry.lr:.3f} m**"
        )
        col_tw1, col_tw2 = st.columns(2)
        with col_tw1:
            vp.mass_geometry.track_width_front = st.number_input(
                "Track Width Front (m)", 1.5, 3.2,
                float(vp.mass_geometry.track_width_front), step=0.01, key="vp_tw_front"
            )
        with col_tw2:
            vp.mass_geometry.track_width_rear = st.number_input(
                "Track Width Rear (m)", 1.5, 3.2,
                float(vp.mass_geometry.track_width_rear), step=0.01, key="vp_tw_rear"
            )
        vp.mass_geometry.cg_height = st.number_input(
            "CG Height (m)", 0.5, 2.0, float(vp.mass_geometry.cg_height),
            step=0.01, key="vp_cg_height"
        )
        vp.mass_geometry.Iz = st.number_input(
            "Yaw Inertia Iz (kg·m²)", 5000.0, 40000.0,
            float(vp.mass_geometry.Iz), step=500.0, key="vp_iz"
        )

    with st.expander("🛞 Tires"):
        vp.tire.friction_coefficient = st.number_input(
            "μ (Base Friction Coefficient)", 0.6, 1.8,
            float(vp.tire.friction_coefficient), step=0.05, key="vp_mu"
        )
        vp.tire.wheel_radius = st.number_input(
            "Rolling Wheel Radius (m)", 0.3, 0.8,
            float(vp.tire.wheel_radius), step=0.01, key="vp_wheel_radius"
        )
        col_cf, col_cr = st.columns(2)
        with col_cf:
            vp.tire.cornering_stiffness_front = st.number_input(
                "Cornering Stiffness Front Cf (N/rad)", 50000.0, 300000.0,
                float(vp.tire.cornering_stiffness_front), step=5000.0, key="vp_cf"
            )
        with col_cr:
            vp.tire.cornering_stiffness_rear = st.number_input(
                "Cornering Stiffness Rear Cr (N/rad)", 50000.0, 300000.0,
                float(vp.tire.cornering_stiffness_rear), step=5000.0, key="vp_cr"
            )
        st.markdown("**Pacejka Magic Formula (advanced)**")
        col_b, col_c, col_d, col_e = st.columns(4)
        with col_b:
            vp.tire.pacejka_B = st.number_input(
                "B (stiffness)", 4.0, 20.0, float(vp.tire.pacejka_B),
                step=0.5, key="vp_pac_b"
            )
        with col_c:
            vp.tire.pacejka_C = st.number_input(
                "C (shape)", 1.0, 2.0, float(vp.tire.pacejka_C),
                step=0.05, key="vp_pac_c"
            )
        with col_d:
            vp.tire.pacejka_D = st.number_input(
                "D (peak)", 0.5, 2.0, float(vp.tire.pacejka_D),
                step=0.05, key="vp_pac_d"
            )
        with col_e:
            vp.tire.pacejka_E = st.number_input(
                "E (curvature)", 0.5, 1.0, float(vp.tire.pacejka_E),
                step=0.01, key="vp_pac_e"
            )

    with st.expander("🔥 Engine"):
        vp.engine.max_power = st.number_input(
            "Power (kW)", 200.0, 1000.0, float(vp.engine.max_power) / 1000.0,
            step=10.0, key="vp_power"
        ) * 1000.0
        vp.engine.max_torque = st.number_input(
            "Max Torque (Nm)", 1000.0, 6500.0, float(vp.engine.max_torque),
            step=50.0, key="vp_torque"
        )
        col_rmax, col_ridle = st.columns(2)
        with col_rmax:
            vp.engine.rpm_max = st.number_input(
                "RPM Limit", 1500.0, 4000.0, float(vp.engine.rpm_max),
                step=100.0, key="vp_rpm_max"
            )
        with col_ridle:
            vp.engine.rpm_idle = st.number_input(
                "Idle RPM", 500.0, 1200.0, float(vp.engine.rpm_idle),
                step=50.0, key="vp_rpm_idle"
            )

    with st.expander("📈 Engine / Torque Curve"):
        render_torque_curve_editor(vp, selected_vid)

    with st.expander("⛽ Fuel"):
        vp.engine.bsfc_g_per_kwh = st.number_input(
            "BSFC (g/kWh)", 150.0, 350.0, float(vp.engine.bsfc_g_per_kwh),
            step=5.0, key="vp_bsfc",
            help="Brake-specific fuel consumption at high load. Fuel use "
                 "is computed dynamically as BSFC × instantaneous power × dt; "
                 "the resulting consumption (L and L/km) is shown in Results."
        )
        vp.fuel_density_kg_per_l = st.number_input(
            "Fuel Density (kg/L)", 0.70, 0.90, float(vp.fuel_density_kg_per_l),
            step=0.01, key="vp_fuel_density"
        )

    with st.expander("⚙️ Transmission"):
        num_gears = st.slider(
            "Number of Gears", 4, 16, int(vp.transmission.num_gears),
            key="vp_num_gears"
        )
        ratios = _resample_gear_ratios(vp.transmission.gear_ratios, num_gears)
        ratio_df = pd.DataFrame({
            "Gear": list(range(1, num_gears + 1)),
            "Ratio": ratios,
        })
        edited = st.data_editor(
            ratio_df,
            hide_index=True,
            column_config={
                "Gear": st.column_config.NumberColumn("Gear", disabled=True),
                "Ratio": st.column_config.NumberColumn(
                    "Ratio", min_value=0.3, max_value=25.0, step=0.01, format="%.3f"
                ),
            },
            key=f"vp_gears_{selected_vid}_{num_gears}",
        )
        vp.transmission.num_gears = num_gears
        vp.transmission.gear_ratios = [float(r) for r in edited["Ratio"].tolist()]
        vp.transmission.final_drive_ratio = st.number_input(
            "Final Drive Ratio", 2.0, 8.5,
            float(vp.transmission.final_drive_ratio), step=0.05, key="vp_final_drive"
        )
        vp.transmission.shift_time = st.number_input(
            "Shift Time (s)", 0.05, 1.0, float(vp.transmission.shift_time),
            step=0.05, key="vp_shift_time"
        )

    with st.expander("🛑 Brakes"):
        vp.brake.max_deceleration = st.slider(
            "Max deceleration limit (m/s²)", 3.0, 12.0,
            float(vp.brake.max_deceleration), step=0.1, key="vp_max_decel"
        )
        vp.brake.brake_balance = st.slider(
            "Front Brake Bias (%)", 30.0, 80.0, float(vp.brake.brake_balance),
            step=0.5, key="vp_brake_balance",
            help="Coupled to longitudinal load transfer: deceleration is "
                 "capped at the first-axle-lockup limit for this bias."
        )
        vp.brake.max_brake_force = st.number_input(
            "Max Total Brake Force (N)", 20000.0, 120000.0,
            float(vp.brake.max_brake_force), step=1000.0, key="vp_brake_force"
        )
        vp.brake.disc_thermal_efficiency = st.slider(
            "Disc Thermal Efficiency", 0.5, 1.0,
            float(vp.brake.disc_thermal_efficiency), step=0.01,
            key="vp_disc_eff",
            help="Fraction of dissipated kinetic energy absorbed by the "
                 "discs (preliminary thermal model input)."
        )

    with st.expander("🌬️ Aerodynamics"):
        vp.aero.drag_coefficient = st.number_input(
            "Drag Coefficient Cd", 0.3, 1.4, float(vp.aero.drag_coefficient),
            step=0.01, key="vp_cd"
        )
        vp.aero.lift_coefficient = st.number_input(
            "Lift Coefficient Cl (negative = downforce)", -2.0, 1.0,
            float(vp.aero.lift_coefficient), step=0.01, key="vp_cl"
        )
        vp.aero.frontal_area = st.number_input(
            "Frontal Area (m²)", 4.0, 12.0, float(vp.aero.frontal_area),
            step=0.1, key="vp_frontal_area"
        )

    st.markdown("---")
    if st.button("💾 Save Truck Setup", width="stretch", type="primary"):
        # Enforce regulatory mass of 4950 kg (vehicle + pilot)
        if vp.mass_geometry.mass < 4950.0:
            vp.mass_geometry.mass = 4950.0
        st.session_state.vehicle_params = vp
        st.session_state.setup = None
        st.session_state.confirmed_mode = "Copa Truck"
        st.session_state.params_saved = True
        st.rerun()

    if st.session_state.params_saved and st.session_state.confirmed_mode == "Copa Truck":
        st.success(f"✅ **{vp.name}** configuration saved — ready to simulate.")
