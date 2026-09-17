"""
Pure mapping between the flat solver params dict (to_solver_dict /
from_solver_dict contract) and the relational vehicle tables.

Keeping the mapping declarative and side-effect free lets the
decompose/recompose round-trip be unit-tested without a database, and
gives db_manager a single source of truth for column names.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger("src.database.vehicle_mapping")

# table -> {flat_solver_key: column_name}
FLAT_TO_TABLES: Dict[str, Dict[str, str]] = {
    "vehicle_mass_geometry": {
        "m": "mass_kg",
        "lf": "lf_m",
        "lr": "lr_m",
        "h_cg": "cg_height_m",
        "track_width_front": "track_width_front_m",
        "track_width_rear": "track_width_rear_m",
        "Iz": "iz_kgm2",
        "k_roll_front": "k_roll_front",
        "k_roll_rear": "k_roll_rear",
    },
    "vehicle_tires": {
        "Cf": "cf_n_per_rad",
        "Cr": "cr_n_per_rad",
        "mu": "mu",
        "r_wheel": "wheel_radius_m",
        "pacejka_B": "pacejka_b",
        "pacejka_C": "pacejka_c",
        "pacejka_D": "pacejka_d",
        "pacejka_E": "pacejka_e",
        "P_cold_bar": "p_cold_bar",
        "P_cold_lf_psi": "p_cold_lf_psi",
        "P_cold_fr_psi": "p_cold_fr_psi",
        "P_cold_lr_psi": "p_cold_lr_psi",
        "P_cold_rr_psi": "p_cold_rr_psi",
    },
    "vehicle_engine": {
        "P_max": "max_power_w",
        "T_max": "max_torque_nm",
        "rpm_max": "rpm_max",
        "rpm_idle": "rpm_idle",
        "bsfc": "bsfc_g_per_kwh",
    },
    "vehicle_transmission": {
        "final_drive": "final_drive",
        "shift_time": "shift_time_s",
        "driveline_eff": "driveline_efficiency",
        "upshift_rpm": "upshift_rpm",
        "downshift_rpm": "downshift_rpm",
    },
    "vehicle_brakes": {
        "max_brake_force": "max_brake_force_n",
        "brake_balance": "brake_balance_pct",
        "max_decel": "max_decel_ms2",
        "abs_enabled": "abs_enabled",
        "abs_slip_target": "abs_slip_target",
        "brake_response_time": "brake_response_time_s",
        "disc_thermal_efficiency": "disc_thermal_efficiency",
        "disc_mass_kg": "disc_mass_kg",
        "disc_specific_heat": "disc_specific_heat",
        "disc_convection": "disc_convection",
        "disc_area_m2": "disc_area_m2",
        "disc_initial_temp_c": "disc_initial_temp_c",
        "fade_onset_temp_c": "fade_onset_temp_c",
        "fade_full_temp_c": "fade_full_temp_c",
        "fade_min_factor": "fade_min_factor",
    },
    "vehicle_aero": {
        "Cx": "cx",
        "A_front": "frontal_area_m2",
        "Cl": "cl",
    },
    "vehicle_fuel": {
        "initial_fuel_l": "initial_fuel_l",
        "fuel_density": "fuel_density_kg_per_l",
        "fuel_per_km": "fuel_per_km_l",
    },
}

# Flat keys handled outside the 1:1 tables or derived on recompose
_LIST_KEYS = {"gear_ratios", "torque_curve_rpm", "torque_curve_nm"}
_DERIVED_KEYS = {"n_gears", "track_width", "k_roll"}  # k_roll = front + rear
_IDENTITY_KEYS = {"name", "manufacturer", "year", "category"}


def decompose_params(
    params: Dict[str, Any],
) -> Tuple[Dict[str, Dict[str, Any]], List[Tuple[int, float]], List[Tuple[float, float]]]:
    """Split a flat solver dict into per-table rows + gear/torque lists.

    Returns:
        (tables, gears, torque) where tables maps table name ->
        {column: value}, gears is [(gear_number, ratio)] and torque is
        [(rpm, torque_nm)].
    """
    tables: Dict[str, Dict[str, Any]] = {}
    consumed = set(_LIST_KEYS) | _DERIVED_KEYS | _IDENTITY_KEYS

    for table, mapping in FLAT_TO_TABLES.items():
        row = {}
        for flat_key, column in mapping.items():
            if flat_key in params and params[flat_key] is not None:
                row[column] = params[flat_key]
                consumed.add(flat_key)
        if row:
            tables[table] = row

    gears = [
        (i + 1, float(r))
        for i, r in enumerate(params.get("gear_ratios") or [])
    ]
    torque = list(
        zip(
            [float(r) for r in (params.get("torque_curve_rpm") or [])],
            [float(t) for t in (params.get("torque_curve_nm") or [])],
        )
    )

    unknown = set(params) - consumed
    if unknown:
        logger.warning(
            "decompose_params: unmapped solver keys ignored: %s",
            sorted(unknown),
        )
    return tables, gears, torque


def recompose_params(
    tables: Dict[str, Dict[str, Any]],
    gears: List[Tuple[int, float]],
    torque: List[Tuple[float, float]],
) -> Dict[str, Any]:
    """Rebuild the flat solver dict from per-table rows + lists.

    Inverse of decompose_params: derived keys (n_gears, track_width avg)
    are recomputed so the output honours the from_solver_dict contract.
    """
    params: Dict[str, Any] = {}
    for table, mapping in FLAT_TO_TABLES.items():
        row = tables.get(table) or {}
        for flat_key, column in mapping.items():
            if column in row and row[column] is not None:
                params[flat_key] = row[column]

    ordered = sorted(gears, key=lambda g: g[0])
    if ordered:
        params["gear_ratios"] = [r for _, r in ordered]
        params["n_gears"] = len(ordered)

    curve = sorted(torque, key=lambda t: t[0])
    if curve:
        params["torque_curve_rpm"] = [rpm for rpm, _ in curve]
        params["torque_curve_nm"] = [nm for _, nm in curve]

    tw_f = params.get("track_width_front")
    tw_r = params.get("track_width_rear")
    if tw_f is not None and tw_r is not None:
        params["track_width"] = (tw_f + tw_r) / 2.0

    k_f = params.get("k_roll_front")
    k_r = params.get("k_roll_rear")
    if k_f is not None and k_r is not None:
        params["k_roll"] = k_f + k_r

    return params
