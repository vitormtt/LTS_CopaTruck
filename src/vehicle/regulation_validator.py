"""
Technical regulation validator for Copa Truck simulator.

Checks vehicle parameters against the official 2025 technical regulations:
- Total minimum weight (truck + pilot): 4890 kg
- Minimum front axle load (without pilot): 2520 kg
- Wheelbase: 3300 mm +/- 50 mm (3.25 m to 3.85 m)
- Maximum outer width (track width + tire width): 2450 mm + 15 mm (2.465 m)
- Maximum turbo pressure: 2.8 kgf/cm² (gauge)

Author: Lap Time Simulator Team
"""
from typing import List, Dict
from src.vehicle.parameters import VehicleParams

# Reference constants from CBA regulation
MIN_TOTAL_WEIGHT_KG = 4890.0
MIN_FRONT_AXLE_WEIGHT_KG = 2520.0
MIN_WHEELBASE_M = 3.25
MAX_WHEELBASE_M = 3.85
MAX_OUTER_WIDTH_M = 2.465
TYRE_WIDTH_M = 0.315  # standard 315/70 R22.5 truck tyre
MAX_TURBO_PRESSURE_BAR = 2.746  # 2.8 kgf/cm2 = 2.74586 bar


def validate_regulation_compliance(vp: VehicleParams) -> Dict[str, any]:
    """
    Validate vehicle parameters against CBA technical regulations.

    Returns:
        Dict with keys:
            'compliant': bool
            'errors': List[str]
            'warnings': List[str]
    """
    errors: List[str] = []
    warnings: List[str] = []

    # 1. Total Weight check (assuming Race Mass includes the pilot)
    mass = vp.mass_geometry.mass
    if mass < MIN_TOTAL_WEIGHT_KG:
        errors.append(
            f"Minimum total weight (with pilot) must be {MIN_TOTAL_WEIGHT_KG:.0f} kg. "
            f"Current: {mass:.0f} kg."
        )

    # 2. Front axle weight without pilot check
    # Assume static front weight distribution. Without pilot weight (~90 kg),
    # the front axle weight is computed.
    # We estimate: front_load = (mass - 90.0) * weight_distribution_front
    wd_front = vp.mass_geometry.weight_distribution_front
    estimated_pilot_kg = 90.0
    mass_no_pilot = max(mass - estimated_pilot_kg, 3500.0)
    front_load_no_pilot = mass_no_pilot * wd_front
    if front_load_no_pilot < MIN_FRONT_AXLE_WEIGHT_KG:
        errors.append(
            f"Minimum front axle weight (without pilot) must be {MIN_FRONT_AXLE_WEIGHT_KG:.0f} kg. "
            f"Estimated current: {front_load_no_pilot:.0f} kg (Distribution: {wd_front * 100.0:.1f}%)."
        )

    # 3. Wheelbase check
    wb = vp.mass_geometry.wheelbase
    if wb < MIN_WHEELBASE_M or wb > MAX_WHEELBASE_M:
        errors.append(
            f"Wheelbase must be between {MIN_WHEELBASE_M * 1000:.0f} mm and {MAX_WHEELBASE_M * 1000:.0f} mm. "
            f"Current: {wb * 1000:.0f} mm."
        )

    # 4. Outer track width check (track_width + tire_width)
    outer_w_f = vp.mass_geometry.track_width_front + TYRE_WIDTH_M
    outer_w_r = vp.mass_geometry.track_width_rear + TYRE_WIDTH_M
    if outer_w_f > MAX_OUTER_WIDTH_M:
        errors.append(
            f"Maximum outer front width exceeds regulation limit of {MAX_OUTER_WIDTH_M * 1000:.0f} mm. "
            f"Current: {outer_w_f * 1000:.0f} mm."
        )
    if outer_w_r > MAX_OUTER_WIDTH_M:
        errors.append(
            f"Maximum outer rear width exceeds regulation limit of {MAX_OUTER_WIDTH_M * 1000:.0f} mm. "
            f"Current: {outer_w_r * 1000:.0f} mm."
        )

    # 5. Turbo pressure check
    # Standard racing diesels turbo limits can be estimated from map, or warning if engine parameters are extreme.
    # We could check if we have a turbo pressure field in engine or warn in general if torque is excessive.
    # Since there is no explicit turbo_pressure field in EngineParams, we will check if the user exceeded typical power levels for the limit.
    if vp.engine.max_power > 880000.0:  # ~1200 cv
        warnings.append(
            f"High power capacity selected ({vp.engine.max_power/1000:.0f} kW). "
            f"Ensure boost pressure remains compliant with the {MAX_TURBO_PRESSURE_BAR:.2f} bar limit (2.8 kgf/cm²)."
        )

    return {
        "compliant": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }
