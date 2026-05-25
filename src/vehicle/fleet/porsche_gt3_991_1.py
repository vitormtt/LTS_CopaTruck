"""
Porsche 911 GT3 Cup (991 Fase 1) — vehicle parameters for lap time simulation.

Model year: 2013–2016 (Carrera Cup Brasil / GT3 Cup Challenge Brasil)
Engine:     3.8L NA flat-6, 338 kW (460 hp) @ 7.500 rpm
Transmission: 6-speed sequential pneumatic (APS paddle shift)
Category:   GT3 Cup

Geometry note:
    lf = 1.33 m, lr = 1.52 m  =>  wheelbase = 2.85 m
    (the 911 road car has 2.450 m; the GT3 Cup has a modified rear subframe
    that shifts the rear axle rearward, lengthening the wheelbase)

Parameter sources:
    - Porsche Motorsport GT3 Cup Type 991 Technical Description (IMSA, 2017)
    - ENG210319 Manual 991.1 — Carrera Cup Brasil (2021) [internal]
    - Rajamani (2012), Pacejka (2012)

Author: Lap Time Simulator Team
Date: 2026-03-10
"""

from ..parameters import (
    VehicleParams, VehicleMassGeometry, TireParams,
    AeroParams, EngineParams, TransmissionParams, BrakeParams,
)

_LF = 1.33   # [m] CG to front axle
_LR = 1.52   # [m] CG to rear axle


def porsche_gt3_cup_991_1() -> VehicleParams:
    """
    Default parameters for Porsche 911 GT3 Cup 991 Fase 1.

    Returns:
        VehicleParams: Complete vehicle parameter set.
    """
    return VehicleParams(
        mass_geometry=VehicleMassGeometry(
            mass=1050.0,
            lf=_LF,
            lr=_LR,
            wheelbase=_LF + _LR,          # 2.85 m — derived, always consistent
            track_width_front=1.580,
            track_width_rear=1.550,
            cg_height=0.480,
            Iz=1250.0,
            Ix=380.0,
            Iy=1100.0,
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
            max_torque=440.0,
            rpm_max=8500.0,
            rpm_idle=900.0,
            rpm_redline=8500.0,
            torque_curve_rpm=[
                1000.0, 2000.0, 3000.0, 4000.0, 5000.0,
                6000.0, 6500.0, 7000.0, 7500.0, 8000.0, 8500.0,
            ],
            torque_curve_nm=[
                200.0, 280.0, 350.0, 390.0, 420.0,
                440.0, 435.0, 425.0, 410.0, 385.0, 340.0,
            ],
            max_coolant_temp=110.0,
            max_oil_temp=140.0,
        ),
        transmission=TransmissionParams(
            num_gears=6,
            gear_ratios=[3.82, 2.30, 1.64, 1.27, 1.03, 0.86],
            final_drive_ratio=3.44,
            shift_time=0.050,
            upshift_rpm=8300.0,
            downshift_rpm=5500.0,
            transmission_efficiency=0.96,
        ),
        brake=BrakeParams(
            max_brake_force=28000.0,
            brake_balance=52.0,
            max_deceleration=22.0,
            brake_response_time=0.05,
            abs_enabled=False,
            abs_slip_target=0.15,
        ),
        name="Porsche 911 GT3 Cup (991 Fase 1)",
        manufacturer="Porsche",
        year=2014,
        category="GT3_Cup",
        fuel_consumption_l_per_km=1.5,
    )
