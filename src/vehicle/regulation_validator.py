"""
Technical regulation validator for Copa Truck simulator.

Limits sourced from the official CBA technical regulations (Conselho
Técnico Desportivo Nacional — cba.org.br/upload/downloads):

2025 (copa-truck-regulamento-tecnico-2025, Art. 21.2 / 24 / Fig. 14):
- Minimum total weight (truck + pilot): 4 890 kg
- Minimum front axle load (without pilot): 2 520 kg
- Wheelbase: 3 300–3 800 mm with ±50 mm tolerance (3.25–3.85 m)
- Maximum outer width at the tyre shoulder: 2 450 mm + 15 mm tolerance

2026 (copa-truck-regulamento-tecnico-2026, Art. 21.2):
- Minimum total weight (truck + pilot) raised to 4 950 kg
- The per-axle minimum was REMOVED from Art. 21.2
- Wheelbase and outer-width articles unchanged

Tyre brand/spec is defined per event by the series promoter via the
technical bulletin (Art. 5) — it is not fixed in the rulebook.

Author: Lap Time Simulator Team
"""
from typing import Dict, List, Optional

from src.vehicle.parameters import VehicleParams

# Season being validated. 2026 is the default (upcoming season); switch
# to 2025 to scrutineer against the previous rulebook.
REGULATION_SEASON = 2026

# Per-season limits from the CBA technical regulation (None = no check)
_SEASON_LIMITS: Dict[int, Dict[str, Optional[float]]] = {
    2025: {
        "min_total_weight_kg": 4890.0,
        "min_front_axle_weight_kg": 2520.0,
    },
    2026: {
        "min_total_weight_kg": 4950.0,
        "min_front_axle_weight_kg": None,  # dropped from Art. 21.2 in 2026
    },
}

# Common to both rulebooks
MIN_WHEELBASE_M = 3.25   # 3 300 mm - 50 mm tolerance
MAX_WHEELBASE_M = 3.85   # 3 800 mm + 50 mm tolerance
MAX_OUTER_WIDTH_M = 2.465  # 2 450 mm + 15 mm tolerance, at the tyre shoulder
TYRE_WIDTH_M = 0.315  # promoter-defined truck tyre (see Art. 5); 315-class assumed
MAX_TURBO_PRESSURE_BAR = 2.746  # 2.8 kgf/cm2 = 2.74586 bar
ESTIMATED_PILOT_KG = 90.0


def validate_regulation_compliance(
    vp: VehicleParams,
    season: int = REGULATION_SEASON,
) -> Dict[str, any]:
    """
    Validate vehicle parameters against the CBA technical regulations.

    Args:
        vp: Vehicle to scrutineer.
        season: Rulebook year (2025 or 2026).

    Returns:
        Dict with keys:
            'compliant': bool
            'errors': List[str]
            'warnings': List[str]
            'season': int
    """
    limits = _SEASON_LIMITS.get(season, _SEASON_LIMITS[REGULATION_SEASON])
    errors: List[str] = []
    warnings: List[str] = []

    # 1. Total weight check (race mass includes the pilot)
    min_total = limits["min_total_weight_kg"]
    mass = vp.mass_geometry.mass
    if mass < min_total:
        errors.append(
            f"Minimum total weight (with pilot) must be {min_total:.0f} kg "
            f"(CBA {season}, Art. 21.2). Current: {mass:.0f} kg."
        )

    # 2. Front axle weight without pilot (2025 rulebook only)
    min_front = limits["min_front_axle_weight_kg"]
    if min_front is not None:
        wd_front = vp.mass_geometry.weight_distribution_front
        mass_no_pilot = max(mass - ESTIMATED_PILOT_KG, 3500.0)
        front_load_no_pilot = mass_no_pilot * wd_front
        if front_load_no_pilot < min_front:
            errors.append(
                f"Minimum front axle weight (without pilot) must be "
                f"{min_front:.0f} kg (CBA {season}, Art. 21.2). Estimated "
                f"current: {front_load_no_pilot:.0f} kg "
                f"(Distribution: {wd_front * 100.0:.1f}%)."
            )

    # 3. Wheelbase check (3 300-3 800 mm with +/-50 mm tolerance)
    wb = vp.mass_geometry.wheelbase
    if wb < MIN_WHEELBASE_M or wb > MAX_WHEELBASE_M:
        errors.append(
            f"Wheelbase must be between {MIN_WHEELBASE_M * 1000:.0f} mm and "
            f"{MAX_WHEELBASE_M * 1000:.0f} mm (CBA, suspension article). "
            f"Current: {wb * 1000:.0f} mm."
        )

    # 4. Outer width at the tyre shoulder (2 450 mm + 15 mm tolerance)
    outer_w_f = vp.mass_geometry.track_width_front + TYRE_WIDTH_M
    outer_w_r = vp.mass_geometry.track_width_rear + TYRE_WIDTH_M
    if outer_w_f > MAX_OUTER_WIDTH_M:
        errors.append(
            f"Maximum outer front width exceeds regulation limit of "
            f"{MAX_OUTER_WIDTH_M * 1000:.0f} mm. Current: {outer_w_f * 1000:.0f} mm."
        )
    if outer_w_r > MAX_OUTER_WIDTH_M:
        errors.append(
            f"Maximum outer rear width exceeds regulation limit of "
            f"{MAX_OUTER_WIDTH_M * 1000:.0f} mm. Current: {outer_w_r * 1000:.0f} mm."
        )

    # 5. Turbo pressure advisory (pop-off valve calibrated per event)
    if vp.engine.max_power > 880000.0:  # ~1200 cv
        warnings.append(
            f"High power capacity selected ({vp.engine.max_power/1000:.0f} kW). "
            f"Ensure boost pressure remains compliant with the "
            f"{MAX_TURBO_PRESSURE_BAR:.2f} bar limit (2.8 kgf/cm²)."
        )

    return {
        "compliant": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "season": season,
    }
