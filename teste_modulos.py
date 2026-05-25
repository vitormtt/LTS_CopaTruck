from src.vehicle.engine import ICEEngine
from src.vehicle.brakes import PneumaticBrake
from src.vehicle.truck_models import build_copa_truck

print("--- PARTE 1: TESTE DE MÓDULOS ISOLADOS ---")

# Criar motor do Caminhão
motor_caminhao = ICEEngine({
    'displacement': 12.0,
    'max_power_kw': 335,      # 450 HP
    'max_power_rpm': 2000,
    'max_torque_nm': 1600,
    'max_torque_rpm': 1200
})
torque = motor_caminhao.get_max_torque(1500)
print(f"Torque do motor a 1500 RPM: {torque:.2f} Nm")

# Criar Freio Pneumático do Caminhão
freio_caminhao = PneumaticBrake({
    'wheel_radius_m': 0.5,
    'max_brake_torque_nm': 8000
})
forcas = freio_caminhao.get_brake_force(brake_pressure=1.0, wheel_speed=50)
print(
    f"Força de frenagem Dianteira gerada pelo tambor pneumático: {forcas['front']:.2f} N")

print("\n--- PARTE 2: TESTE DO MODELO DINÂMICO COMPLETO (2-DOF) ---")

# 1. Constrói o caminhão inteiro (Motor, Freio, Pneu e Chassi conectados)
truck = build_copa_truck()

# 2. Seta o estado inicial (Andando a 80 km/h)
truck.vx = 22.2  # m/s

# 3. Testando 100% de Acelerador, 0 de Freio, e 0.05 radianos de esterçamento do volante
derivadas = truck.calculate_derivatives(
    throttle=1.0,
    brake_pedal=0.0,
    steering_angle=0.05,
    current_rpm=1800
)

# Imprimindo a física resultante gerada pela união dos sistemas
print(f"Força Longitudinal na Roda (Fx): {derivadas['Fx_total']:.2f} N")
print(f"Força Lateral Dianteira (Fy_f): {derivadas['Fy_f']:.2f} N")
print(f"Força Lateral Traseira (Fy_r): {derivadas['Fy_r']:.2f} N")
print(f"Aceleração Longitudinal (Ax): {derivadas['ax']:.2f} m/s^2")
print(f"Aceleração Lateral (Ay): {derivadas['ay']:.2f} m/s^2")
print(
    f"Taxa de Yaw Accel (Momento no eixo Z): {derivadas['yaw_accel']:.2f} rad/s^2")
