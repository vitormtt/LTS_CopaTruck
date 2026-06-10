"""
Vehicle parameters configuration page for the Streamlit UI.

Author: Lap Time Simulator Team
Date: 2026-06-06
"""
import streamlit as st
from src.vehicle.fleet import get_vehicle_by_id, list_vehicles
from src.vehicle.setup import VehicleSetup, apply_setup
from .helpers import init_session_state


def parametros_veiculo_page() -> None:
    st.header("🚗 Vehicle Parameters & Setup")
    init_session_state()

    mode = st.radio(
        "Select Vehicle Category:",
        ["Copa Truck", "Porsche GT3 Cup"],
        horizontal=True,
        key="vehicle_mode"
    )

    all_vehicles = list_vehicles()

    # Filter vehicle list based on selected category
    if mode == "Copa Truck":
        category_vehicles = {
            vid: name for vid, name in all_vehicles.items()
            if "volkswagen" in vid or "scania" in vid or "volvo" in vid or "copa" in vid.lower()
        }
    else:
        category_vehicles = {
            vid: name for vid, name in all_vehicles.items()
            if "porsche" in vid
        }

    if not category_vehicles:
        st.error(f"No vehicles found registered for category: {mode}")
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

    # ---- Setup / Parameter Customization ----
    if mode == "Copa Truck":
        st.subheader("🔧 Customize Truck Parameters")
        if st.radio("Enable parameter customization?", ["No", "Yes"], horizontal=True) == "Yes":
            sec = st.radio(
                "Section:",
                ["Mass/Geometry", "Tire", "Engine", "Fuel", "Transmission", "Brake", "Aerodynamics"],
                horizontal=True
            )
            
            if sec == "Mass/Geometry":
                vp.mass_geometry.mass = st.number_input(
                    "Race Mass (kg)", 4950.0, 9000.0, max(float(vp.mass_geometry.mass), 4950.0), step=50.0
                )
                wb = st.number_input(
                    "Wheelbase (m)", 3.0, 5.5, float(vp.mass_geometry.wheelbase), step=0.05
                )
                vp.mass_geometry.lf = st.number_input(
                    "CG to Front Axle (m)", 1.0, 3.5, float(vp.mass_geometry.lf), step=0.05
                )
                vp.mass_geometry.lr = wb - vp.mass_geometry.lf
                vp.mass_geometry.wheelbase = wb
                
            elif sec == "Tire":
                vp.tire.friction_coefficient = st.number_input(
                    "μ (Base Friction Coefficient)", 0.6, 1.8, float(vp.tire.friction_coefficient), step=0.05
                )
                vp.tire.wheel_radius = st.number_input(
                    "Rolling Wheel Radius (m)", 0.3, 0.8, float(vp.tire.wheel_radius), step=0.01
                )
                vp.tire.cold_pressure_bar = st.number_input(
                    "Cold Tyre Pressure (bar)", 1.0, 3.5, float(vp.tire.cold_pressure_bar), step=0.1
                )
                
            elif sec == "Engine":
                vp.engine.max_power = st.number_input(
                    "Power (kW)", 200.0, 1000.0, float(vp.engine.max_power) / 1000.0, step=10.0
                ) * 1000.0
                vp.engine.max_torque = st.number_input(
                    "Max Torque (Nm)", 1000.0, 6500.0, float(vp.engine.max_torque), step=50.0
                )
                vp.engine.rpm_max = st.number_input(
                    "RPM Limit", 1500.0, 4000.0, float(vp.engine.rpm_max), step=100.0
                )
                
            elif sec == "Fuel":
                vp.initial_fuel_l = st.number_input(
                    "Initial Fuel Load (L)", 0.0, 500.0, float(vp.initial_fuel_l), step=5.0
                )
                vp.fuel_consumption_l_per_km = st.number_input(
                    "Fuel Consumption Rate (L/km)", 0.1, 5.0, float(vp.fuel_consumption_l_per_km), step=0.1
                )

            elif sec == "Transmission":
                vp.transmission.num_gears = st.slider(
                    "Number of Gears", 5, 16, int(vp.transmission.num_gears)
                )
                vp.transmission.final_drive_ratio = st.number_input(
                    "Final Drive Ratio", 2.0, 8.5, float(vp.transmission.final_drive_ratio), step=0.05
                )
                
            elif sec == "Brake":
                vp.brake.max_deceleration = st.slider(
                    "Max deceleration limit (m/s²)", 3.0, 12.0, float(vp.brake.max_deceleration), step=0.1
                )
                vp.brake.brake_balance = st.slider(
                    "Front Brake Bias (%)", 30.0, 80.0, float(vp.brake.brake_balance), step=0.5
                )
                
            elif sec == "Aerodynamics":
                vp.aero.drag_coefficient = st.number_input(
                    "Drag Coefficient Cd", 0.3, 1.4, float(vp.aero.drag_coefficient), step=0.01
                )
                vp.aero.frontal_area = st.number_input(
                    "Frontal Area (m²)", 4.0, 12.0, float(vp.aero.frontal_area), step=0.1
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

    # ---- Porsche GT3 Cup / Setup Builder ----------------------------------
    else:
        st.subheader("🔧 Mechanical Setup Builder")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            arb_f = st.slider("ARB Front (Stiff)", 1, 7, 4)
        with col2:
            arb_r = st.slider("ARB Rear (Stiff)", 1, 7, 4)
        with col3:
            wing = st.slider("Wing Position", 1, 9, 5)
        with col4:
            pressure = st.number_input("Tyre P (bar)", 1.4, 2.4, 1.8, step=0.05)
        with col5:
            bias = st.slider("Brake bias", -2.0, 0.0, -1.0, step=0.5)

        setup = VehicleSetup(
            arb_front=arb_f,
            arb_rear=arb_r,
            wing_position=wing,
            tyre_pressure=float(pressure),
            brake_bias=float(bias),
            setup_name=f"ARB{arb_f}/{arb_r}_W{wing}",
        )

        d = setup.to_dict()
        col_i1, col_i2, col_i3, col_i4 = st.columns(4)
        col_i1.metric("ARB Front Stiffness", f"{d['arb_front_stiffness_nm_rad']/1000:.0f} kNm/rad")
        col_i2.metric("ARB Rear Stiffness", f"{d['arb_rear_stiffness_nm_rad']/1000:.0f} kNm/rad")
        col_i3.metric("Wing ΔCd", f"{d['wing_delta_cd']:+.3f}")
        col_i4.metric("Handling Balance", d['handling_balance'])

        st.markdown("---")
        if st.button("💾 Save Setup & Parameters", width="stretch", type="primary"):
            params = apply_setup(vp, setup)
            st.session_state.vehicle_params = params
            st.session_state.setup = setup
            st.session_state.confirmed_mode = "Porsche GT3 Cup"
            st.session_state.params_saved = True
            st.rerun()

        if st.session_state.params_saved and st.session_state.confirmed_mode == "Porsche GT3 Cup":
            st.success(
                f"✅ **{vp.name}** + setup **{st.session_state.setup.setup_name}** "
                "saved — ready to simulate."
            )
