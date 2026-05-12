"""
Porsche 911 GT3 Cup (992 Fase 1) — vehicle parameters for lap time simulation.

Model year: 2021–present (Carrera Cup Brasil / GT3 Cup Challenge Brasil)
Engine:     4.0L NA flat-6, 373 kW (510 hp) @ 8.400 rpm
Transmission: 6-speed sequential (PDK-derived, updated logic)
Category:   GT3 Cup

Geometry note:
    lf = 1.34 m, lr = 1.525 m  =>  wheelbase = 2.865 m
    (992 has marginally longer wheelbase vs. 991 due to chassis update)

Key differences vs. 991 Fase 2:
    - Power: 338 kW -> 373 kW (+10.4%)
    - Higher RPM peak: 8.400 rpm
    - Improved aero package (higher Cl, lower Cd)
    - Stiffer chassis (higher Iz)

Parameter sources:
    - Porsche Motorsport 992 GT3 Cup Technical Description (2021)
    - Porsche Newsroom spec sheet (2021)

Author: Lap Time Simulator Team
Date: 2026-03-10
"""

from ..parameters import (
    VehicleParams, VehicleMassGeometry, TireParams,
    AeroParams, EngineParams, TransmissionParams, BrakeParams,
)

_LF = 1.340
_LR = 1.525


def porsche_gt3_cup_992_1() -> VehicleParams:
    """
    Default parameters for Porsche 911 GT3 Cup 992 Fase 1.

    Returns:
        VehicleParams: Complete vehicle parameter set.
    """
    return VehicleParams(
        mass_geometry=VehicleMassGeometry(
            mass=1080.0,
            lf=_LF,
            lr=_LR,
            wheelbase=_LF + _LR,          # 2.865 m
            track_width_front=1.600,
            track_width_rear=1.580,
            cg_height=0.475,
            Iz=1300.0,
            Ix=390.0,
            Iy=1150.0,
        ),
        tire=TireParams(
            cornering_stiffness_front=78000.0,
            cornering_stiffness_rear=88000.0,
            friction_coefficient=1.60,
            wheel_radius=0.330,
            pacejka_B=12.5,
            pacejka_C=1.38,
            pacejka_D=1.60,
            pacejka_E=0.88,
        ),
        aero=AeroParams(
            drag_coefficient=0.36,
            frontal_area=1.93,
            lift_coefficient=-1.05,
            air_density=1.225,
        ),
        engine=EngineParams(
            max_power=373000.0,
            max_torque=470.0,
            rpm_max=8750.0,
            rpm_idle=900.0,
            rpm_redline=8750.0,
            torque_curve_rpm=[
                1000.0, 2000.0, 3000.0, 4000.0, 5000.0,
                6000.0, 7000.0, 7500.0, 8000.0, 8400.0, 8750.0,
            ],
            torque_curve_nm=[
                210.0, 290.0, 360.0, 410.0, 450.0,
                468.0, 470.0, 462.0, 445.0, 420.0, 370.0,
            ],
            max_coolant_temp=110.0,
            max_oil_temp=140.0,
        ),
        transmission=TransmissionParams(
            num_gears=6,
            gear_ratios=[3.91, 2.35, 1.68, 1.30, 1.06, 0.88],
            final_drive_ratio=3.44,
            shift_time=0.045,
            upshift_rpm=8550.0,
            downshift_rpm=5700.0,
            transmission_efficiency=0.96,
        ),
        brake=BrakeParams(
            max_brake_force=30000.0,
            brake_balance=52.0,
            max_deceleration=23.0,
            brake_response_time=0.045,
            abs_enabled=True,
            abs_slip_target=0.10,
        ),
        name="Porsche 911 GT3 Cup (992 Fase 1)",
        manufacturer="Porsche",
        year=2021,
        category="GT3_Cup",
        fuel_consumption_l_per_km=1.5,
    )
