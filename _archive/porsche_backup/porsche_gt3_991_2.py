"""
Porsche 911 GT3 Cup (991 Fase 2) — vehicle parameters for lap time simulation.

Model year: 2017–2019 (Carrera Cup Brasil / GT3 Cup Challenge Brasil)
Engine:     4.0L NA flat-6, 338 kW (460 hp) @ 7.600 rpm
Transmission: 6-speed sequential pneumatic (APS — revised logic vs. Fase 1)
Category:   GT3 Cup

Geometry note:
    lf = 1.33 m, lr = 1.52 m  =>  wheelbase = 2.85 m  (same as 991 Fase 1)

Key differences vs. 991 Fase 1:
    - New 4.0L engine (flatter mid-range torque curve)
    - ABS with 12-position switch (abs_enabled=True)
    - shift_time slightly longer (smoother feel)
    - Iz slightly higher (4.0L engine marginally heavier)

Parameter sources:
    - ENG210319 Manual 991.2 — Carrera Cup Brasil (2021) [internal]
    - Porsche Motorsport Technical Specifications 991.2 (2017)

Author: Lap Time Simulator Team
Date: 2026-03-10
"""

from ..parameters import (
    VehicleParams, VehicleMassGeometry, TireParams,
    AeroParams, EngineParams, TransmissionParams, BrakeParams,
)

_LF = 1.33
_LR = 1.52


def porsche_gt3_cup_991_2() -> VehicleParams:
    """
    Default parameters for Porsche 911 GT3 Cup 991 Fase 2.

    Returns:
        VehicleParams: Complete vehicle parameter set.
    """
    return VehicleParams(
        mass_geometry=VehicleMassGeometry(
            mass=1050.0,
            lf=_LF,
            lr=_LR,
            wheelbase=_LF + _LR,          # 2.85 m
            track_width_front=1.580,
            track_width_rear=1.550,
            cg_height=0.480,
            Iz=1260.0,
            Ix=380.0,
            Iy=1110.0,
        ),
        tire=TireParams(
            cornering_stiffness_front=75000.0,
            cornering_stiffness_rear=85000.0,
            friction_coefficient=1.55,
            wheel_radius=0.330,
            pacejka_B=12.0,
            pacejka_C=1.35,
            pacejka_D=1.55,
            pacejka_E=0.90,
        ),
        aero=AeroParams(
            drag_coefficient=0.38,
            frontal_area=1.90,
            lift_coefficient=-0.85,
            air_density=1.225,
        ),
        engine=EngineParams(
            max_power=338000.0,
            max_torque=460.0,
            rpm_max=8500.0,
            rpm_idle=900.0,
            rpm_redline=8500.0,
            torque_curve_rpm=[
                1000.0, 2000.0, 3000.0, 4000.0, 5000.0,
                6000.0, 6500.0, 7000.0, 7500.0, 8000.0, 8500.0,
            ],
            torque_curve_nm=[
                220.0, 300.0, 370.0, 410.0, 440.0,
                460.0, 455.0, 445.0, 430.0, 400.0, 350.0,
            ],
            max_coolant_temp=110.0,
            max_oil_temp=140.0,
        ),
        transmission=TransmissionParams(
            num_gears=6,
            gear_ratios=[3.82, 2.30, 1.64, 1.27, 1.03, 0.86],
            final_drive_ratio=3.44,
            shift_time=0.060,
            upshift_rpm=8300.0,
            downshift_rpm=5500.0,
            transmission_efficiency=0.96,
        ),
        brake=BrakeParams(
            max_brake_force=28000.0,
            brake_balance=52.0,
            max_deceleration=22.0,
            brake_response_time=0.05,
            abs_enabled=True,
            abs_slip_target=0.10,
        ),
        name="Porsche 911 GT3 Cup (991 Fase 2)",
        manufacturer="Porsche",
        year=2017,
        category="GT3_Cup",
        fuel_consumption_l_per_km=1.5,
    )
