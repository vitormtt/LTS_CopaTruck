from src.vehicle.engine import ICEEngine, ElectricMotor
from src.vehicle.brakes import HydraulicBrake, PneumaticBrake
from src.vehicle.transmission import Transmission
from src.vehicle.tires import LinearTire, PacejkaTire
from src.vehicle.vehicle_model import BicycleVehicle2DOF

def build_copa_truck():
    """Factory para instanciar o modelo 2-DOF parametrizado como Copa Truck"""
    engine = ICEEngine({
        'displacement': 12.0,
        'max_power_kw': 335,
        'max_power_rpm': 2000,
        'max_torque_nm': 1600,
        'max_torque_rpm': 1200
    })
    
    brakes = PneumaticBrake({
        'wheel_radius_m': 0.53, # ~1048mm diameter tyre
        'max_brake_torque_nm': 8000,
        'chamber_area_cm2': 800
    })
    
    trans = Transmission({
        'gear_ratios': [6.36, 3.83, 2.38, 1.54, 1.00, 0.77],
        'final_drive': 4.11
    })
    
    tires = PacejkaTire({
        'mu_y': 0.85, # Caminhão tem menos grip lateral
        'pacejka_b_y': 12.0,
        'pacejka_c_y': 1.2
    })
    
    return BicycleVehicle2DOF(
        mass=5500,        # kg
        wheelbase=3.8,    # m
        a=1.82,           # CG distance to front
        cg_height=1.2,    # alto
        izz=15000,        # kg*m2
        engine_sys=engine,
        brake_sys=brakes,
        trans_sys=trans,
        tire_sys=tires
    )


def build_passenger_car():
    """Factory para sedan (validação em literatura)"""
    engine = ICEEngine({
        'displacement': 2.0,
        'max_power_kw': 160,
        'max_power_rpm': 5500,
        'max_torque_nm': 350,
        'max_torque_rpm': 1500
    })
    
    brakes = HydraulicBrake({
        'wheel_radius_m': 0.32,
        'max_brake_torque_nm': 3000
    })
    
    trans = Transmission({
        'gear_ratios': [3.5, 2.0, 1.4, 1.0, 0.8, 0.65],
        'final_drive': 3.5
    })
    
    tires = LinearTire({
        'cornering_stiffness': 60000, # N/rad
        'mu_y': 1.0
    })
    
    return BicycleVehicle2DOF(
        mass=1400,
        wheelbase=2.6,
        a=1.3,
        cg_height=0.5,
        izz=2500,
        engine_sys=engine,
        brake_sys=brakes,
        trans_sys=trans,
        tire_sys=tires
    )
