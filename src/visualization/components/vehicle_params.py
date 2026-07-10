"""
Vehicle parameters configuration page for the Streamlit UI.

Exposes the full VehicleParams field set (mass/geometry, tires,
engine, fuel, transmission, brakes, aerodynamics) grouped in
expanders. Field-friendly units (tyre pressure in psi) are converted
exactly once at the widget boundary via src.vehicle.units.

Author: Lap Time Simulator Team
Date: 2026-06-06
"""
import re

import numpy as np
import pandas as pd
import streamlit as st

from src.database import db_manager
from src.vehicle.fleet import (
    fleet_source,
    get_vehicle_by_id,
    list_vehicles,
    refresh_fleet,
)
from .helpers import init_session_state
from .torque_curve import render_torque_curve_editor

# Cold pressure UI range mapped to the safe truck setup window (6.55–8.62 bar)
_PRESSURE_PSI_MIN = 95.0
_PRESSURE_PSI_MAX = 125.0

# Session-state prefixes owned by this page's parameter widgets. They must
# be dropped when the selected vehicle changes: Streamlit ignores a
# widget's `value=` once its key exists, so stale keys would silently
# overwrite the freshly loaded model with the previous model's numbers.
_WIDGET_KEY_PREFIXES = ("vp_", "pres_", "new_model_")


def _reset_param_widget_state() -> None:
    """Forget widget values so inputs re-seed from the selected vehicle."""
    for key in list(st.session_state.keys()):
        if key.startswith(_WIDGET_KEY_PREFIXES):
            del st.session_state[key]


def _resample_gear_ratios(ratios: list, num_gears: int) -> list:
    """Resample a gear-ratio list to a new gear count, preserving shape."""
    if len(ratios) == num_gears:
        return [float(r) for r in ratios]
    old_idx = np.linspace(0.0, 1.0, len(ratios))
    new_idx = np.linspace(0.0, 1.0, num_gears)
    return [float(r) for r in np.interp(new_idx, old_idx, ratios)]


from src.vehicle.regulation_validator import validate_regulation_compliance

def parametros_veiculo_page() -> None:
    st.header("Vehicle Parameters")
    st.caption("Configure design specs and race setup — save to arm the simulation.")
    init_session_state()

    # The whole active fleet is Copa Truck (incl. user-created models) —
    # filtering by manufacturer substring would hide new custom models.
    category_vehicles = list_vehicles()

    if not category_vehicles:
        st.error("No Copa Truck vehicles found in the fleet registry.")
        return

    # Surface the success message from a model created on the previous run
    created_msg = st.session_state.pop("model_created_msg", None)
    if created_msg:
        st.success(created_msg)

    # Select vehicle model (index pinned so reruns keep the active selection)
    vehicle_ids = list(category_vehicles.keys())
    if st.session_state.vehicle_id not in category_vehicles:
        st.session_state.vehicle_id = vehicle_ids[0]

    col_sel, col_refresh = st.columns([5, 1])
    with col_sel:
        selected_vid = st.selectbox(
            "Choose Model:",
            options=vehicle_ids,
            index=vehicle_ids.index(st.session_state.vehicle_id),
            format_func=lambda x: category_vehicles[x]
        )
    with col_refresh:
        st.caption(f"source: {fleet_source()}")
        if st.button(
            "↻ Refresh", key="btn_refresh_fleet", width="stretch",
            help="Reload fleet data from storage and re-seed the inputs "
                 "below (the model list also auto-refreshes every 5 s)."
        ):
            refresh_fleet()
            _reset_param_widget_state()
            st.session_state.vehicle_params = None
            st.rerun()

    # If selection changed, reload params and drop stale widget state
    if selected_vid != st.session_state.vehicle_id or st.session_state.vehicle_params is None:
        if selected_vid != st.session_state.vehicle_id:
            _reset_param_widget_state()
        st.session_state.vehicle_id = selected_vid
        st.session_state.vehicle_params = get_vehicle_by_id(selected_vid)
        st.session_state.params_saved = False
        st.session_state.setup = None
        st.rerun()

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

    # Split page into 2 main columns: Setup Settings vs Design Specifications
    col_setup, col_project = st.columns(2)

    with col_setup:
        st.subheader("Setup Settings (Ajustes de Pista)")
        
        # 1. Individual Tyre Pressure in PSI
        st.markdown("**Tyre Cold Pressure (psi)**")
        col_pres_lf, col_pres_fr = st.columns(2)
        with col_pres_lf:
            pres_lf = st.number_input(
                "Front Left (LF)", _PRESSURE_PSI_MIN, _PRESSURE_PSI_MAX,
                float(vp.tire.cold_pressure_lf_psi), step=0.5, key="pres_lf"
            )
        with col_pres_fr:
            pres_fr = st.number_input(
                "Front Right (FR)", _PRESSURE_PSI_MIN, _PRESSURE_PSI_MAX,
                float(vp.tire.cold_pressure_fr_psi), step=0.5, key="pres_fr"
            )
            
        col_pres_lr, col_pres_rr = st.columns(2)
        with col_pres_lr:
            pres_lr = st.number_input(
                "Rear Left (LR)", _PRESSURE_PSI_MIN, _PRESSURE_PSI_MAX,
                float(vp.tire.cold_pressure_lr_psi), step=0.5, key="pres_lr"
            )
        with col_pres_rr:
            pres_rr = st.number_input(
                "Rear Right (RR)", _PRESSURE_PSI_MIN, _PRESSURE_PSI_MAX,
                float(vp.tire.cold_pressure_rr_psi), step=0.5, key="pres_rr"
            )
            
        vp.tire.cold_pressure_lf_psi = pres_lf
        vp.tire.cold_pressure_fr_psi = pres_fr
        vp.tire.cold_pressure_lr_psi = pres_lr
        vp.tire.cold_pressure_rr_psi = pres_rr
        # Sync the average pressure bar for solver compatibility
        vp.tire.cold_pressure_bar = (pres_lf + pres_fr + pres_lr + pres_rr) / 4.0 / 14.5038
        st.caption(f"Average Pressure: {vp.tire.cold_pressure_bar:.2f} bar")

        # 2. Fuel Load
        vp.initial_fuel_l = st.number_input(
            "Initial Fuel Load (L)", 0.0, 500.0, float(vp.initial_fuel_l),
            step=5.0, key="vp_initial_fuel",
            help="Drives the dynamic vehicle mass as fuel burns during the lap."
        )

        # 3. Brake Balance
        vp.brake.brake_balance = st.slider(
            "Front Brake Bias (%)", 30.0, 80.0, float(vp.brake.brake_balance),
            step=0.5, key="vp_brake_balance",
            help="Coupled to longitudinal load transfer."
        )

        # 4. Aerodynamics Setup
        st.markdown("**Aerodynamics Setup**")
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

    with col_project:
        st.subheader("Design Specifications (Projeto)")

        # 1. Mass & Geometry
        with st.expander("Mass and Geometry"):
            vp.mass_geometry.mass = st.number_input(
                "Race Mass (kg)", 4000.0, 9000.0,
                max(float(vp.mass_geometry.mass), 4000.0), step=50.0, key="vp_mass"
            )
            wb = st.number_input(
                "Wheelbase (m)", 3.0, 5.5, float(vp.mass_geometry.wheelbase),
                step=0.05, key="vp_wheelbase"
            )
            wd_front = st.slider(
                "Front Static Weight Distribution (%)", 30.0, 70.0,
                float(vp.mass_geometry.weight_distribution_front * 100.0),
                step=0.5, key="vp_wd_front",
                help="lf and lr are recomputed from wheelbase and this split."
            )
            vp.mass_geometry.wheelbase = wb
            vp.mass_geometry.lr = wb * (wd_front / 100.0)
            vp.mass_geometry.lf = wb - vp.mass_geometry.lr
            st.caption(
                f"CG to front axle (lf): {vp.mass_geometry.lf:.3f} m | "
                f"CG to rear axle (lr): {vp.mass_geometry.lr:.3f} m"
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
            col_k1, col_k2 = st.columns(2)
            with col_k1:
                vp.k_roll_front = st.number_input(
                    "Roll Stiffness Front (N·m/rad)", 10000.0, 300000.0,
                    float(vp.k_roll_front), step=5000.0, key="vp_k_roll_f"
                )
            with col_k2:
                vp.k_roll_rear = st.number_input(
                    "Roll Stiffness Rear (N·m/rad)", 10000.0, 300000.0,
                    float(vp.k_roll_rear), step=5000.0, key="vp_k_roll_r"
                )
            vp.k_roll = vp.k_roll_front + vp.k_roll_rear

        # 2. Tires Base Specs
        with st.expander("Tires Specification"):
            vp.tire.friction_coefficient = st.number_input(
                "Base Friction Coefficient (mu)", 0.6, 1.8,
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
            st.markdown("Pacejka Magic Formula Coefficients")
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

        # 3. Engine Base Specs + Torque Curve Editor Unified
        with st.expander("Engine Parameters and Torque Curve"):
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
            vp.engine.bsfc_g_per_kwh = st.number_input(
                "BSFC (g/kWh)", 150.0, 350.0, float(vp.engine.bsfc_g_per_kwh),
                step=5.0, key="vp_bsfc",
                help="Brake-specific fuel consumption."
            )
            vp.fuel_density_kg_per_l = st.number_input(
                "Fuel Density (kg/L)", 0.70, 0.90, float(vp.fuel_density_kg_per_l),
                step=0.01, key="vp_fuel_density"
            )
            st.markdown("---")
            st.markdown("**Interactive Torque Curve Editor**")
            render_torque_curve_editor(vp, selected_vid)

        # 4. Transmission
        with st.expander("Transmission"):
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

        # 5. Brakes Base Specs
        with st.expander("Brakes Specification"):
            vp.brake.max_deceleration = st.slider(
                "Max deceleration limit (m/s²)", 3.0, 12.0,
                float(vp.brake.max_deceleration), step=0.1, key="vp_max_decel"
            )
            derived_force = vp.derived_brake_force()
            if derived_force is not None:
                st.metric("Brake force derived from hardware",
                          f"{derived_force / 1000.0:.1f} kN")
                hw_f, hw_r = vp.brake.hardware_front, vp.brake.hardware_rear
                st.caption(
                    f"Limpert chain — {hw_f['n_pistons']}×"
                    f"{hw_f['piston_diameter_m'] * 1000:.0f} mm pistons, "
                    f"{hw_f['line_pressure_bar']:.0f}/"
                    f"{hw_r['line_pressure_bar']:.0f} bar F/R equivalent, "
                    f"pad µ {hw_f['pad_friction']:.2f}, "
                    f"disc R {hw_f['disc_effective_radius_m'] * 1000:.1f} mm. "
                    "Manual force input below is IGNORED while hardware is set "
                    "(grip still caps the lap).")
            vp.brake.max_brake_force = st.number_input(
                "Max Total Brake Force (N)", 20000.0, 120000.0,
                float(vp.brake.max_brake_force), step=1000.0, key="vp_brake_force"
            )


    st.markdown("---")
    
    # Run Technical Regulation Validation Checks
    validation = validate_regulation_compliance(vp)
    if not validation["compliant"]:
        st.error("Regulation Non-Compliance Errors:")
        for err in validation["errors"]:
            st.write(f"- {err}")
    if validation["warnings"]:
        st.warning("Regulation Warnings:")
        for warn in validation["warnings"]:
            st.write(f"- {warn}")

    if st.button("Save Truck Setup", width="stretch", type="primary", disabled=not validation["compliant"]):
        st.session_state.vehicle_params = vp
        st.session_state.setup = None
        st.session_state.confirmed_mode = "Copa Truck"
        st.session_state.params_saved = True
        st.rerun()

    if st.session_state.params_saved and st.session_state.confirmed_mode == "Copa Truck":
        st.success(f"{vp.name} configuration saved — ready to simulate.")

    _render_save_as_new_model(vp, category_vehicles, validation)


def _slugify_model_id(text: str) -> str:
    """Normalize free text into a fleet-registry id (lowercase snake_case)."""
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return re.sub(r"_+", "_", slug)


def _render_save_as_new_model(vp, existing_vehicles: dict, validation: dict) -> None:
    """Persist the currently edited parameters as a brand-new fleet model.

    The form starts pre-filled from the selected vehicle, so creating a
    variant is: pick base model -> tweak inputs -> name it -> save. The
    new model is written through db_manager (PostgreSQL with JSON
    fallback) and becomes immediately selectable in the fleet.
    """
    st.markdown("---")
    with st.expander("Create New Model (save current inputs as a copy)"):
        st.caption(
            "Saves every input above as a new fleet model — the base "
            "models stay untouched. Storage: PostgreSQL when available, "
            "data/vehicle_models.json fallback otherwise."
        )
        col_name, col_id = st.columns(2)
        with col_name:
            new_name = st.text_input(
                "Model Name", value=f"{vp.name} (Copy)", key="new_model_name"
            )
        with col_id:
            suggested_id = _slugify_model_id(new_name or vp.name)
            new_id = st.text_input(
                "Model ID", value=suggested_id, key="new_model_id",
                help="Unique registry key (lowercase letters, numbers, _)."
            )
        col_manu, col_year = st.columns(2)
        with col_manu:
            new_manufacturer = st.text_input(
                "Manufacturer", value=vp.manufacturer or "", key="new_model_manufacturer"
            )
        with col_year:
            new_year = st.number_input(
                "Year", 1990, 2035, int(vp.year) if vp.year else 2024,
                step=1, key="new_model_year"
            )

        if not validation["compliant"]:
            st.info("Resolve the regulation errors above to enable saving.")

        if st.button(
            "Save as New Model", width="stretch",
            disabled=not validation["compliant"], key="btn_save_new_model"
        ):
            model_id = _slugify_model_id(new_id)
            if not model_id:
                st.error("Model ID cannot be empty.")
            elif model_id in existing_vehicles:
                st.error(
                    f"Model ID '{model_id}' already exists — choose another "
                    "ID to avoid overwriting a fleet model."
                )
            elif not (new_name or "").strip():
                st.error("Model Name cannot be empty.")
            else:
                saved = db_manager.save_vehicle(
                    vehicle_id=model_id,
                    name=new_name.strip(),
                    manufacturer=new_manufacturer.strip(),
                    year=int(new_year),
                    category="Truck",
                    params=vp.to_solver_dict(),
                )
                if saved:
                    refresh_fleet()
                    st.session_state.vehicle_id = model_id
                    st.session_state.vehicle_params = None
                    st.session_state.params_saved = False
                    st.session_state.model_created_msg = (
                        f"Model '{new_name.strip()}' created as '{model_id}' — "
                        "now selected."
                    )
                    st.rerun()
                else:
                    st.error(
                        "Failed to persist the new model (database and JSON "
                        "fallback both unavailable). Check the logs."
                    )



