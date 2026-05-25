# src/optimization.py
"""
Otimizador de tempo de volta com restrições realistas
Método: Forward/Backward com fatiamento de potência
"""
import numpy as np
from scipy.optimize import minimize

def compute_optimal_speed_profile(circuit, vehicle_params, mu_adhesion, method="forward_backward"):
    """
    Calcula perfil de velocidade ótimo respeitando:
    - Limite de curva (aceleração lateral)
    - Limite de motor (potência/torque)
    - Limite de frenagem
    - Limite de aderência (círculo de força)
    """
    x = circuit.centerline_x
    y = circuit.centerline_y
    n = len(x)
    
    # Curvatura
    ds = np.sqrt(np.diff(x)**2 + np.diff(y)**2)
    ds = np.concatenate([[0], ds])
    s_cum = np.cumsum(ds)
    
    dx = np.gradient(x)
    dy = np.gradient(y)
    ddx = np.gradient(dx)
    ddy = np.gradient(dy)
    curvature = (dx * ddy - dy * ddx) / (dx**2 + dy**2 + 1e-6)**1.5
    radius = np.where(np.abs(curvature) > 1e-6, 1.0 / np.abs(curvature), 1e6)
    radius = np.clip(radius, 10.0, 1e6)
    
    g = 9.81
    rho = 1.225
    
    # ===== FORWARD PASS =====
    v_fwd = np.zeros(n)
    v_fwd[0] = 5.0  # largada
    
    for i in range(1, n):
        v_prev = v_fwd[i-1]
        
        # Limite lateral
        v_lat_max = np.sqrt(mu_adhesion * g * radius[i])
        
        # Gear selection: lowest gear (highest traction) with RPM within limits
        r_wheel = vehicle_params["r_wheel"]
        final_drive = vehicle_params["final_drive"]
        rpm_max = vehicle_params["rpm_max"]
        ratio = vehicle_params["gear_ratios"][-1] * final_drive  # fallback: highest gear
        for gr in vehicle_params["gear_ratios"]:
            ratio_cand = gr * final_drive
            rpm_cand = (max(v_prev, 0.01) / r_wheel) * ratio_cand * 60 / (2 * np.pi)
            if rpm_cand <= rpm_max:
                ratio = ratio_cand  # lowest gear within RPM limit = max traction
                break

        rpm = (max(v_prev, 0.01) / r_wheel) * ratio * 60 / (2 * np.pi)

        # Tração disponível
        F_trac = min(
            vehicle_params["P_max"] / max(v_prev, 1.0),
            0.9 * mu_adhesion * vehicle_params["m"] * g
        )
        a_max = F_trac / vehicle_params["m"]
        
        # Integra velocidade
        v_possible = np.sqrt(max(0, v_prev**2 + 2 * a_max * ds[i]))
        v_fwd[i] = min(v_possible, v_lat_max, 150.0 / 3.6)
    
    # ===== BACKWARD PASS =====
    v_opt = np.copy(v_fwd)
    for i in reversed(range(n-1)):
        v_next = v_opt[i+1]
        a_lat_next = v_next**2 / max(radius[i+1], 1.0)
        a_decel_max = np.sqrt(max(0, (mu_adhesion * g)**2 - a_lat_next**2))
        a_decel_max = min(a_decel_max, vehicle_params["max_decel"])
        
        if ds[i+1] > 0:
            v_brake_limit = np.sqrt(v_next**2 + 2 * a_decel_max * ds[i+1])
            v_opt[i] = min(v_opt[i], v_brake_limit)
    
    return v_opt, s_cum, radius
