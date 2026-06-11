# src/simulation/lap_time_solver.py
"""
Simulador de Lap Time — Solver principal

Ponto de entrada principal: run_simulation(config, vehicle_params, circuit)
Legacy entry point preservado: run_bicycle_model(params_dict, circuit, config)

Modos suportados (via SimulationMode):
  QUALIFYING    — volta de classificação a partir de velocidade de equilíbrio
  FLYING_LAP    — volta com velocidade de entrada prescrita (v_entry_kmh)
  STANDING_START— largada parada com modelo de patinagem e rampa de embreagem

O solver aplica VehicleSetup automaticamente antes de resolver,
modificando parâmetros de aero, pneus e freio conforme configurado.

Output: SimulationResult com canais de telemetria alinhados ao
nomenclador Pi Toolbox / MoTeC (Porsche Carrera Cup Brasil).

Referencias
-----------
Brayshaw & Harrison (2005). A quasi steady state approach to race
  car lap simulation. Proc. IMechE Part D, 219(3), 383-394.
Segers, J. (2014). Analysis Techniques for Racecar Data Acquisition,
  2nd Ed. SAE International.
"""

from __future__ import annotations

import logging
import time as _time
from dataclasses import dataclass, field
from typing import Dict, Optional

import numpy as np
import pandas as pd

from .simulation_modes import SimulationConfig, SimulationMode
from ..vehicle.parameters import VehicleParams
from ..vehicle.setup import apply_setup_to_params

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Legacy local VehicleParams dataclass (kept for run_bicycle_model compat)
# ---------------------------------------------------------------------------

@dataclass
class _LegacyVehicleParams:
    """Internal flat params used by legacy run_bicycle_model only."""
    m: float = 5000.0
    lf: float = 2.1
    lr: float = 2.3
    h_cg: float = 1.1
    Cf: float = 120000.0
    Cr: float = 120000.0
    mu: float = 1.1
    r_wheel: float = 0.65
    P_max: float = 600000.0
    T_max: float = 3700.0
    rpm_max: float = 2800.0
    rpm_idle: float = 800.0
    n_gears: int = 12
    gear_ratios: list = None
    final_drive: float = 5.33
    max_decel: float = 7.5
    brake_balance: float = 58.0
    max_brake_force: float = 50000.0
    bsfc: float = 210.0
    # Brake disc thermal model (ENDURANCE_THERMAL)
    disc_thermal_efficiency: float = 0.90
    disc_mass_kg: float = 30.0
    disc_specific_heat: float = 460.0
    disc_convection: float = 60.0
    disc_area_m2: float = 0.35
    disc_initial_temp_c: float = 60.0
    fade_onset_temp_c: float = 450.0
    fade_full_temp_c: float = 800.0
    fade_min_factor: float = 0.5
    Cx: float = 0.85
    A_front: float = 8.7
    Cl: float = 0.0
    k_roll_front: float = 115_000.0
    k_roll_rear: float = 115_000.0
    track_width: float = 1.565
    fuel_per_km: float = 1.5
    speed_limit: float = 999.0
    initial_fuel_l: float = 100.0
    fuel_density: float = 0.85

    def __post_init__(self):
        if self.gear_ratios is None:
            self.gear_ratios = [14.0, 10.5, 7.8, 5.9, 4.5, 3.5, 2.7, 2.1,
                                 1.6, 1.25, 1.0, 0.78]
        self.L = self.lf + self.lr
        self.Iz = self.m * (self.lf**2 + self.lr**2) / 2


# ---------------------------------------------------------------------------
# SimulationResult
# ---------------------------------------------------------------------------

@dataclass
class SimulationResult:
    """
    Output container for a completed simulation run.

    All array channels are 1-D numpy arrays of length n (number of track
    points). Scalar KPIs are pre-computed at construction.

    Attributes
    ----------
    lap_time : float
        Total simulated lap time [s].
    mode : SimulationMode
        Mode used for this simulation.
    setup_name : str
        Name tag of the VehicleSetup applied.
    distance : np.ndarray
        Cumulative distance along track [m].
    time : np.ndarray
        Cumulative lap time at each point [s].
    v_kmh : np.ndarray
        Speed [km/h].
    ax_long_g : np.ndarray
        Longitudinal acceleration [g]. Positive = acceleration.
    ay_lat_g : np.ndarray
        Lateral acceleration [g]. Positive = left.
    throttle_pct : np.ndarray
        Throttle demand [0–100 %].
    brake_pct : np.ndarray
        Brake demand [0–100 %].
    steering_deg : np.ndarray
        Estimated steering wheel angle [deg].
    gear : np.ndarray
        Engaged gear (integer).
    rpm : np.ndarray
        Engine RPM.
    radius : np.ndarray
        Track corner radius at each point [m].
    temp_tyre_c : np.ndarray
        Tyre bulk temperature [degC].
    tyre_pressure_bar : np.ndarray
        Hot tyre pressure estimate [bar].
    fuel_used_l : np.ndarray
        Cumulative fuel consumption [L].
    """
    lap_time: float
    mode: SimulationMode
    setup_name: str

    distance: np.ndarray
    time: np.ndarray
    v_kmh: np.ndarray
    ax_long_g: np.ndarray
    ay_lat_g: np.ndarray
    throttle_pct: np.ndarray
    brake_pct: np.ndarray
    steering_deg: np.ndarray
    gear: np.ndarray
    rpm: np.ndarray
    radius: np.ndarray
    temp_tyre_c: np.ndarray
    tyre_pressure_bar: np.ndarray
    fuel_used_l: np.ndarray

    # Raw (m/s²) versions kept for internal use
    _a_long_ms2: np.ndarray = field(repr=False, default=None)
    _a_lat_ms2: np.ndarray = field(repr=False, default=None)

    # ENDURANCE_THERMAL channels (None in other modes)
    disc_temp_front_c: Optional[np.ndarray] = None
    disc_temp_rear_c: Optional[np.ndarray] = None
    brake_fade_factor: Optional[np.ndarray] = None

    # -----------------------------------------------------------------------
    # KPI properties
    # -----------------------------------------------------------------------

    @property
    def avg_speed_kmh(self) -> float:
        return float(np.mean(self.v_kmh))

    @property
    def max_speed_kmh(self) -> float:
        return float(np.max(self.v_kmh))

    @property
    def peak_lat_g(self) -> float:
        return float(np.max(np.abs(self.ay_lat_g)))

    @property
    def peak_brake_g(self) -> float:
        return float(np.min(self.ax_long_g))

    @property
    def peak_accel_g(self) -> float:
        return float(np.max(self.ax_long_g))

    @property
    def time_wot_pct(self) -> float:
        """Percentage of lap with throttle >= 95%."""
        return float(np.mean(self.throttle_pct >= 95.0) * 100.0)

    @property
    def time_braking_pct(self) -> float:
        """Percentage of lap with brake > 5%."""
        return float(np.mean(self.brake_pct > 5.0) * 100.0)

    @property
    def fuel_total_l(self) -> float:
        return float(self.fuel_used_l[-1])

    @property
    def final_tyre_temp_c(self) -> float:
        return float(self.temp_tyre_c[-1])

    @property
    def final_tyre_pressure_bar(self) -> float:
        return float(self.tyre_pressure_bar[-1])

    @property
    def peak_disc_temp_c(self) -> Optional[float]:
        """Peak brake disc temperature [degC] (None outside thermal mode)."""
        if self.disc_temp_front_c is None:
            return None
        return float(max(np.max(self.disc_temp_front_c),
                         np.max(self.disc_temp_rear_c)))

    @property
    def min_fade_factor(self) -> Optional[float]:
        """Worst brake fade factor [-] (None outside thermal mode)."""
        if self.brake_fade_factor is None:
            return None
        return float(np.min(self.brake_fade_factor))

    def to_dataframe(self) -> pd.DataFrame:
        """Export all channels to a tidy DataFrame (MoTeC/Pi Toolbox compatible)."""
        df = pd.DataFrame({
            "distance_m":     self.distance,
            "lap_time_s":     self.time,
            "v_kmh":          self.v_kmh,
            "ax_long_g":      self.ax_long_g,
            "ay_lat_g":       self.ay_lat_g,
            "throttle_pct":   self.throttle_pct,
            "brake_pct":      self.brake_pct,
            "steering_deg":   self.steering_deg,
            "gear":           self.gear,
            "rpm":            self.rpm,
            "radius_m":       self.radius,
            "temp_tyre_c":    self.temp_tyre_c,
            "tyre_press_bar": self.tyre_pressure_bar,
            "fuel_used_l":    self.fuel_used_l,
        })
        if self.disc_temp_front_c is not None:
            df["disc_temp_front_c"] = self.disc_temp_front_c
            df["disc_temp_rear_c"] = self.disc_temp_rear_c
            df["brake_fade_factor"] = self.brake_fade_factor
        return df

    def save_csv(self, path: str) -> None:
        """Save telemetry to CSV. Filename format compatible with existing app."""
        self.to_dataframe().to_csv(path, index=False)
        logger.info(f"[OK] Telemetria salva em: {path}")

    def log_kpis(self) -> None:
        """Log performance KPIs to INFO."""
        logger.info(
            f"[RESULT] [{self.mode.name}] Setup='{self.setup_name}' | "
            f"Lap={self.lap_time:.2f}s | "
            f"V_avg={self.avg_speed_kmh:.1f} km/h | "
            f"V_max={self.max_speed_kmh:.1f} km/h | "
            f"Peak_lat={self.peak_lat_g:.2f}g | "
            f"WOT={self.time_wot_pct:.1f}% | "
            f"Braking={self.time_braking_pct:.1f}% | "
            f"T_tyre={self.final_tyre_temp_c:.1f}\u00b0C | "
            f"Fuel={self.fuel_total_l:.2f}L"
        )


# ---------------------------------------------------------------------------
# Internal helper functions
# ---------------------------------------------------------------------------

def _build_flat_params(vp: VehicleParams) -> _LegacyVehicleParams:
    """Convert structured VehicleParams to flat legacy struct for the solver loop."""
    d = vp.to_solver_dict()
    p = _LegacyVehicleParams(**{k: v for k, v in d.items()
                                 if k in _LegacyVehicleParams.__dataclass_fields__})
    # Set speed limit for trucks (200 km/h = 55.56 m/s to match qualifying telemetry)
    if vp.category == "Truck" or "truck" in vp.name.lower():
        p.speed_limit = 200.0 / 3.6

    else:
        p.speed_limit = 999.0
    return p



def _compute_track_geometry(circuit) -> tuple:
    """Compute ds, s, curvature radius arrays from circuit centerline."""
    x = circuit.centerline_x
    y = circuit.centerline_y
    n = len(x)

    ds = np.zeros(n)
    ds[1:] = np.sqrt(np.diff(x) ** 2 + np.diff(y) ** 2)
    s = np.cumsum(ds)

    dx = np.gradient(x)
    dy = np.gradient(y)
    ddx = np.gradient(dx)
    ddy = np.gradient(dy)

    # Suppress divide-by-zero RuntimeWarning on straight segments
    with np.errstate(divide='ignore', invalid='ignore'):
        curvature = (dx * ddy - dy * ddx) / (dx ** 2 + dy ** 2 + 1e-9) ** 1.5
        radius = np.where(np.abs(curvature) > 1e-6,
                          1.0 / np.abs(curvature), 1e6)
    radius = np.clip(radius, 10.0, 1e6)

    return x, y, n, ds, s, radius


def _torque_curve(rpm: float, p: _LegacyVehicleParams) -> float:
    """Engine torque [N·m] at given RPM. Diesel heavy truck character."""
    rpm_torque_max = 1300.0
    if rpm < p.rpm_idle:
        return 0.0
    elif rpm <= rpm_torque_max:
        return p.T_max * (rpm - p.rpm_idle) / (rpm_torque_max - p.rpm_idle)
    elif rpm <= p.rpm_max:
        return p.T_max * np.exp(-0.0015 * (rpm - rpm_torque_max) ** 1.2)
    else:
        return 0.0


def _torque_curve_interp(
    rpm: float,
    torque_curve_rpm: list,
    torque_curve_nm: list,
    rpm_max: float,
) -> float:
    """Interpolated torque from VehicleParams engine map."""
    if not torque_curve_rpm:
        return 0.0
    if rpm > rpm_max:
        return 0.0  # Rev-limiter fuel cut
    rpm_c = float(np.clip(rpm, torque_curve_rpm[0], torque_curve_rpm[-1]))
    return float(np.interp(rpm_c, torque_curve_rpm, torque_curve_nm))


def _select_gear_optimal(v: float, p: _LegacyVehicleParams) -> int:
    """Select gear that maximises drive force within RPM range."""
    rpm_min_opt = p.rpm_idle * 1.5
    rpm_max_opt = p.rpm_max * 0.90
    best_gear, best_force = 1, -1.0
    for gear in range(1, p.n_gears + 1):
        ratio_total = p.gear_ratios[gear - 1] * p.final_drive
        rpm = (v / max(p.r_wheel, 0.01)) * ratio_total * 60.0 / (2 * np.pi)
        if rpm > p.rpm_max:
            continue
        rpm = max(rpm, p.rpm_idle)
        T = _torque_curve(rpm, p)
        F = T * ratio_total / p.r_wheel
        if rpm_min_opt <= rpm <= rpm_max_opt:
            if F > best_force:
                best_force = F
                best_gear = gear
        elif best_force < 0:
            best_gear = gear
    return best_gear


def _get_rpm(v: float, gear: int, p: _LegacyVehicleParams) -> float:
    """Engine RPM at speed v in given gear."""
    if gear < 1 or gear > p.n_gears:
        return p.rpm_idle
    ratio_total = p.gear_ratios[gear - 1] * p.final_drive
    rpm = (v / max(p.r_wheel, 0.01)) * ratio_total * 60.0 / (2 * np.pi)
    # Clip at idle but allow overrevving past rpm_max to trigger rev-limiter torque drop
    return float(np.maximum(rpm, p.rpm_idle))



def _driver_inputs_from_accel(
    a_long: np.ndarray,
    v_kmh: np.ndarray,
    max_decel: float = 10.0,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Derive throttle_pct and brake_pct from longitudinal acceleration.

    QSS solver is binary: forward pass = full throttle, backward pass = full
    brake. Throttle is 100% wherever a_long > 0; brake scales linearly with
    deceleration magnitude up to max_decel.
    """
    throttle = np.where(a_long > 0.0, 100.0, 0.0)
    brake    = np.clip((-a_long / max(max_decel, 1e-6)) * 100.0, 0.0, 100.0)
    return throttle, brake


def _steering_from_radius(
    radius: np.ndarray,
    v_ms: np.ndarray,
    wheelbase: float,
    steering_ratio: float = 15.0,
) -> np.ndarray:
    """Estimate steering wheel angle from Ackermann geometry."""
    delta_rad = wheelbase / np.maximum(radius, 1.0)
    delta_deg = np.degrees(delta_rad) * steering_ratio
    return delta_deg


def _fuel_step(
    power_w: float,
    dt: float,
    bsfc: float,
    fuel_density: float,
) -> float:
    """
    Fuel burned over one solver step from BSFC and instantaneous power.

    Mirrors ICEEngine.get_fuel_consumption() in src/vehicle/engine.py
    (single source of truth for the formula):

        fuel_kg = bsfc [g/kWh] * P [kW] * dt [h] / 1000
        fuel_L  = fuel_kg / fuel_density

    Zero power (coasting/braking with overrun fuel cut) burns no fuel.
    ``dt`` is clamped to 2.0 s per step so the near-zero speeds of a
    standing-start launch cannot produce a spurious fuel spike.

    Args:
        power_w: Delivered engine power [W] (>= 0).
        dt: Step duration [s].
        bsfc: Brake-specific fuel consumption [g/kWh].
        fuel_density: Fuel density [kg/L].

    Returns:
        Fuel burned in this step [L].
    """
    if power_w <= 0.0:
        return 0.0
    dt_clamped = min(dt, 2.0)
    fuel_kg = bsfc * (power_w / 1000.0) * (dt_clamped / 3600.0) / 1000.0
    return fuel_kg / fuel_density


def _bias_limited_decel(
    p: _LegacyVehicleParams,
    mu_eff: float,
    m_cur: float,
    F_normal: float,
) -> float:
    """
    Maximum deceleration before either axle locks, given the brake bias.

    Under deceleration ``a`` the longitudinal load transfer shifts
    ``m*a*h_cg/L`` from the rear axle to the front axle. With a front
    bias fraction ``b`` the first-lock deceleration per axle is:

        front-limited: a_f = mu*g_eff*(lr/L) / (b - mu*h_cg/L)
        rear-limited:  a_r = mu*g_eff*(lf/L) / ((1-b) + mu*h_cg/L)

    where ``g_eff = F_normal/m_cur`` accounts for aerodynamic downforce.
    The front limit only exists when ``b > mu*h_cg/L`` (otherwise load
    transfer keeps the front axle below lock-up at any deceleration).
    The total brake-force capacity caps the result as well.

    References: Limpert (1999), Brake Design and Safety, ch. 7.

    Args:
        p: Flat solver parameters (geometry, brake bias, brake force).
        mu_eff: Effective tyre-road friction coefficient [-].
        m_cur: Current vehicle mass including fuel [kg].
        F_normal: Total normal force including downforce [N].

    Returns:
        Maximum bias-limited deceleration [m/s²].
    """
    g_eff = F_normal / m_cur
    b = p.brake_balance / 100.0
    mu_h_over_l = mu_eff * p.h_cg / p.L

    a_rear = mu_eff * g_eff * (p.lf / p.L) / ((1.0 - b) + mu_h_over_l)
    candidates = [a_rear]

    if b > mu_h_over_l:
        a_front = mu_eff * g_eff * (p.lr / p.L) / (b - mu_h_over_l)
        candidates.append(a_front)

    candidates.append(p.max_brake_force / m_cur)
    return max(min(candidates), 0.0)


# ---------------------------------------------------------------------------
# Core GGV solver
# ---------------------------------------------------------------------------

def _run_ggv_solver(
    p, x, y, n, ds, s, radius, mu, v0,
    fuel_per_km, temp_ini, p_tyre_cold,  # fuel_per_km unused — reads p.fuel_per_km
    torque_map_rpm, torque_map_nm,
) -> dict:
    """GGV forward + backward pass solver."""
    g = 9.81
    rho = 1.225

    v_profile    = np.zeros(n)
    a_long       = np.zeros(n)
    a_lat        = np.zeros(n)
    gear_profile = np.ones(n, dtype=int)
    rpm_profile  = np.zeros(n)
    temp_tyre    = np.ones(n) * temp_ini
    fuel_acum    = np.zeros(n)

    # ARB load-sensitivity model
    # The axle with the higher ARB fraction bears more lateral load transfer,
    # which degrades grip (load-sensitivity of tyre Fz-mu curve).
    _K_LS = 0.20                                          # grip loss per unit Fz fraction
    _k_roll_total = max(p.k_roll_front + p.k_roll_rear, 1.0)
    _arb_frac_max = max(p.k_roll_front, p.k_roll_rear) / _k_roll_total
    _Fz_static    = p.m * g / 2.0                         # per-axle static load [N]
    _tw           = max(p.track_width, 0.5)

    # Tyre thermal model constants
    _T_AMBIENT = 25.0    # [degC]
    _T_SCALE   = 100.0   # [degC] rise at 2g combined load above ambient
    _TAU_TYRE  = 50.0    # [s] thermal time constant

    v_profile[0] = v0
    gear_profile[0] = _select_gear_optimal(v0, p) if v0 > 0 else 1

    for i in range(1, n):
        v_prev = v_profile[i - 1]
        gear   = _select_gear_optimal(v_prev, p)
        gear_profile[i] = gear

        rpm = _get_rpm(v_prev, gear, p)
        rpm_profile[i - 1] = rpm

        if torque_map_rpm:
            T_engine = _torque_curve_interp(rpm, torque_map_rpm, torque_map_nm, p.rpm_max)
        else:
            T_engine = _torque_curve(rpm, p)

        ratio_total = p.gear_ratios[gear - 1] * p.final_drive
        F_traction  = T_engine * ratio_total / p.r_wheel
        F_drag      = 0.5 * rho * p.Cx * p.A_front * v_prev ** 2
        F_downforce = 0.5 * rho * abs(p.Cl) * p.A_front * v_prev ** 2

        # Dynamic mass (fuel_acum[i-1] is the provisional forward-pass
        # estimate; the time-integration loop recomputes it exactly)
        m_fuel_initial = p.initial_fuel_l * p.fuel_density
        fuel_burned_kg = fuel_acum[i - 1] * p.fuel_density
        m_cur = p.m + max(m_fuel_initial - fuel_burned_kg, 0.0)

        F_normal    = m_cur * g + F_downforce
        a_lat_cur   = v_prev ** 2 / max(radius[i], 1.0)
        F_lat_used  = m_cur * a_lat_cur

        # ARB load-sensitivity: grip penalty on the more loaded axle
        delta_fz_frac = np.clip(
            m_cur * a_lat_cur * p.h_cg * _arb_frac_max / (_tw * _Fz_static),
            0.0, 0.95
        )
        mu_eff = mu * (1.0 - _K_LS * delta_fz_frac)

        v_lat_max   = np.sqrt(mu_eff * g * radius[i])
        F_trac_grip = np.sqrt(max((mu_eff * F_normal) ** 2 - F_lat_used ** 2, 0.0))
        F_traction  = min(F_traction, F_trac_grip)

        a = (F_traction - F_drag) / m_cur
        a_long[i - 1] = a

        if ds[i] > 0:
            v_possible   = np.sqrt(max(0.0, v_prev ** 2 + 2 * a * ds[i]))
            v_profile[i] = min(v_possible, v_lat_max, p.speed_limit)
        else:
            v_profile[i] = min(v_prev, p.speed_limit)


        # Tyre thermal — asymptotic model with dissipation
        a_combined   = np.sqrt(a ** 2 + a_lat_cur ** 2)
        T_ideal      = _T_AMBIENT + _T_SCALE * min(a_combined / (2.0 * g), 1.0)
        dt_step      = ds[i] / max(v_profile[i], 0.1)
        temp_tyre[i] = temp_tyre[i - 1] + (dt_step / _TAU_TYRE) * (T_ideal - temp_tyre[i - 1])

        # Provisional fuel from BSFC x delivered power (forward-pass
        # estimate used by the dynamic-mass terms above)
        P_engine = max(F_traction, 0.0) * v_prev
        fuel_acum[i] = fuel_acum[i - 1] + _fuel_step(
            P_engine, dt_step, p.bsfc, p.fuel_density
        )

    # Forward loop writes [i-1]; fill last element explicitly
    a_long[n - 1]      = a_long[n - 2]
    rpm_profile[n - 1] = _get_rpm(v_profile[n - 1], gear_profile[n - 1], p)

    for i in reversed(range(n - 1)):
        v_next      = v_profile[i + 1]
        a_lat_next  = v_next ** 2 / max(radius[i + 1], 1.0)

        # Dynamic mass for backward pass
        m_fuel_initial = p.initial_fuel_l * p.fuel_density
        fuel_burned_kg = fuel_acum[i + 1] * p.fuel_density
        m_cur_bw = p.m + max(m_fuel_initial - fuel_burned_kg, 0.0)

        delta_fz_f  = np.clip(
            m_cur_bw * a_lat_next * p.h_cg * _arb_frac_max / (_tw * _Fz_static),
            0.0, 0.95
        )
        mu_eff_bwd  = mu * (1.0 - _K_LS * delta_fz_f)

        F_downforce_next = 0.5 * rho * abs(p.Cl) * p.A_front * v_next ** 2
        F_normal_next    = m_cur_bw * g + F_downforce_next
        a_decel_max = min(
            np.sqrt(max(0.0, (mu_eff_bwd * F_normal_next / m_cur_bw) ** 2 - a_lat_next ** 2)),
            p.max_decel,
            _bias_limited_decel(p, mu_eff_bwd, m_cur_bw, F_normal_next),
        )
        if ds[i + 1] > 0:
            v_brake_limit = np.sqrt(v_next ** 2 + 2 * a_decel_max * ds[i + 1])
            v_profile[i]  = min(v_profile[i], v_brake_limit)

    time_profile = np.zeros(n)
    m_fuel_initial = p.initial_fuel_l * p.fuel_density

    for i in range(n):
        a_lat[i] = v_profile[i] ** 2 / max(radius[i], 1.0)
        if i > 0 and v_profile[i] > 0:
            dt = ds[i] / v_profile[i]
            time_profile[i] = time_profile[i - 1] + dt

            # Authoritative fuel: delivered power reconstructed from the
            # final speed profile (zero in braking/coasting zones)
            v_prev_t = v_profile[i - 1]
            a_actual = ((v_profile[i] ** 2 - v_prev_t ** 2) / (2.0 * ds[i])
                        if ds[i] > 0 else 0.0)
            m_cur_t = p.m + max(m_fuel_initial - fuel_acum[i - 1] * p.fuel_density, 0.0)
            F_drag_t = 0.5 * rho * p.Cx * p.A_front * v_prev_t ** 2
            F_engine = m_cur_t * a_actual + F_drag_t
            P_engine = min(max(F_engine, 0.0) * max(v_prev_t, 0.0), p.P_max)
            fuel_acum[i] = fuel_acum[i - 1] + _fuel_step(
                P_engine, dt, p.bsfc, p.fuel_density
            )

    p_tyre_hot = p_tyre_cold + 0.012 * np.maximum(temp_tyre - 25.0, 0.0)

    return {
        "time_profile": time_profile,
        "v_profile":    v_profile,
        "a_long":       a_long,
        "a_lat":        a_lat,
        "gear_profile": gear_profile,
        "rpm_profile":  rpm_profile,
        "temp_tyre":    temp_tyre,
        "tyre_pressure":p_tyre_hot,
        "fuel_acum":    fuel_acum,
    }


# ---------------------------------------------------------------------------
# Brake disc thermal model (ENDURANCE_THERMAL mode)
# ---------------------------------------------------------------------------

def _run_thermal_brake_model(
    v_profile: np.ndarray,
    ds: np.ndarray,
    p: _LegacyVehicleParams,
    ambient_temp_c: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Lumped-mass disc temperature and fade traces for a speed profile.

    Per braking step, the dissipated kinetic power routed to the discs is

        q = eta_disc * m * |a_brake| * v

    split front/rear by the brake balance and onto two discs per axle.
    Each axle's lumped disc integrates

        m_d * c_p * dT = (q_disc - h(v) * A * (T - T_amb)) * dt

    with speed-scaled forced convection h(v) = h0 * (1 + 0.04 v)
    (rotating-disc forced convection, Limpert 1999). The fade factor
    degrades linearly from 1.0 at fade_onset_temp_c down to
    fade_min_factor at fade_full_temp_c, driven by the hotter axle.

    Args:
        v_profile: Speed at each track point [m/s].
        ds: Segment lengths [m].
        p: Flat solver parameters (brake thermal fields).
        ambient_temp_c: Ambient air temperature [degC].

    Returns:
        Tuple (T_front, T_rear, fade_factor) — arrays of length n.
    """
    n = len(v_profile)
    T_front = np.full(n, p.disc_initial_temp_c)
    T_rear = np.full(n, p.disc_initial_temp_c)
    fade = np.ones(n)

    m_total = p.m + p.initial_fuel_l * p.fuel_density
    b_front = p.brake_balance / 100.0
    heat_cap = p.disc_mass_kg * p.disc_specific_heat  # [J/K] per disc

    fade_span = max(p.fade_full_temp_c - p.fade_onset_temp_c, 1e-6)

    for i in range(1, n):
        v_prev = v_profile[i - 1]
        dt = ds[i] / max(v_profile[i], 0.1)
        dt = min(dt, 2.0)

        a_actual = ((v_profile[i] ** 2 - v_prev ** 2) / (2.0 * ds[i])
                    if ds[i] > 0 else 0.0)

        if a_actual < 0.0:
            q_total = p.disc_thermal_efficiency * m_total * (-a_actual) * v_prev
        else:
            q_total = 0.0

        # Two discs per axle
        q_front_disc = q_total * b_front / 2.0
        q_rear_disc = q_total * (1.0 - b_front) / 2.0

        h_conv = p.disc_convection * (1.0 + 0.04 * v_prev)
        for T_arr, q_disc in ((T_front, q_front_disc), (T_rear, q_rear_disc)):
            cooling = h_conv * p.disc_area_m2 * (T_arr[i - 1] - ambient_temp_c)
            T_arr[i] = T_arr[i - 1] + (q_disc - cooling) * dt / heat_cap

        T_hot = max(T_front[i], T_rear[i])
        fade[i] = float(np.clip(
            1.0 - (1.0 - p.fade_min_factor)
            * (T_hot - p.fade_onset_temp_c) / fade_span,
            p.fade_min_factor, 1.0,
        ))

    return T_front, T_rear, fade


def _run_endurance_thermal(
    p, x, y, n, ds, s, radius, mu, v0,
    temp_ini, p_tyre_cold,
    torque_map_rpm, torque_map_nm,
    ambient_temp_c: float,
    thermal_iterations: int,
) -> dict:
    """
    ENDURANCE_THERMAL solver: GGV lap with brake-fade feedback.

    Wraps the standard two-pass GGV solver without modifying it: the
    lap is first solved normally, then the disc thermal model and a
    fade-scaled backward pass iterate to a fixed point (fade only ever
    reduces braking capacity, so the lap time is non-decreasing per
    iteration and convergence is monotonic).

    With fade disabled (onset temperature above any reached disc
    temperature) the output is bit-identical to the QUALIFYING mode.
    """
    g = 9.81
    rho = 1.225

    raw = _run_ggv_solver(
        p=p, x=x, y=y, n=n, ds=ds, s=s, radius=radius,
        mu=mu, v0=v0, fuel_per_km=p.fuel_per_km,
        temp_ini=temp_ini, p_tyre_cold=p_tyre_cold,
        torque_map_rpm=torque_map_rpm,
        torque_map_nm=torque_map_nm,
    )

    # ARB load-sensitivity constants — mirror _run_ggv_solver backward pass
    _K_LS = 0.20
    _k_roll_total = max(p.k_roll_front + p.k_roll_rear, 1.0)
    _arb_frac_max = max(p.k_roll_front, p.k_roll_rear) / _k_roll_total
    _Fz_static = p.m * g / 2.0
    _tw = max(p.track_width, 0.5)
    m_fuel_initial = p.initial_fuel_l * p.fuel_density

    T_front, T_rear, fade = _run_thermal_brake_model(
        raw["v_profile"], ds, p, ambient_temp_c
    )

    for _ in range(max(thermal_iterations, 1)):
        if np.all(fade >= 1.0 - 1e-12):
            break  # no fade: untouched GGV result is the fixed point

        v_profile = raw["v_profile"]
        fuel_acum = raw["fuel_acum"]

        # Fade-scaled backward pass: fade reduces the BRAKE-side caps
        # (system decel limit and bias/lock-up limit); the tyre-grip
        # term is unaffected
        for i in reversed(range(n - 1)):
            v_next = v_profile[i + 1]
            a_lat_next = v_next ** 2 / max(radius[i + 1], 1.0)

            fuel_burned_kg = fuel_acum[i + 1] * p.fuel_density
            m_cur_bw = p.m + max(m_fuel_initial - fuel_burned_kg, 0.0)

            delta_fz_f = np.clip(
                m_cur_bw * a_lat_next * p.h_cg * _arb_frac_max / (_tw * _Fz_static),
                0.0, 0.95
            )
            mu_eff_bwd = mu * (1.0 - _K_LS * delta_fz_f)

            F_downforce_next = 0.5 * rho * abs(p.Cl) * p.A_front * v_next ** 2
            F_normal_next = m_cur_bw * g + F_downforce_next

            brake_cap = min(
                p.max_decel,
                _bias_limited_decel(p, mu_eff_bwd, m_cur_bw, F_normal_next),
            ) * fade[i + 1]
            a_decel_max = min(
                np.sqrt(max(0.0, (mu_eff_bwd * F_normal_next / m_cur_bw) ** 2
                            - a_lat_next ** 2)),
                brake_cap,
            )
            if ds[i + 1] > 0:
                v_brake_limit = np.sqrt(v_next ** 2 + 2 * a_decel_max * ds[i + 1])
                v_profile[i] = min(v_profile[i], v_brake_limit)

        # Recompute time, lateral accel and authoritative fuel
        time_profile = np.zeros(n)
        a_lat = raw["a_lat"]
        for i in range(n):
            a_lat[i] = v_profile[i] ** 2 / max(radius[i], 1.0)
            if i > 0 and v_profile[i] > 0:
                dt = ds[i] / v_profile[i]
                time_profile[i] = time_profile[i - 1] + dt

                v_prev_t = v_profile[i - 1]
                a_actual = ((v_profile[i] ** 2 - v_prev_t ** 2) / (2.0 * ds[i])
                            if ds[i] > 0 else 0.0)
                m_cur_t = p.m + max(
                    m_fuel_initial - fuel_acum[i - 1] * p.fuel_density, 0.0
                )
                F_drag_t = 0.5 * rho * p.Cx * p.A_front * v_prev_t ** 2
                F_engine = m_cur_t * a_actual + F_drag_t
                P_engine = min(max(F_engine, 0.0) * max(v_prev_t, 0.0), p.P_max)
                fuel_acum[i] = fuel_acum[i - 1] + _fuel_step(
                    P_engine, dt, p.bsfc, p.fuel_density
                )
        raw["time_profile"] = time_profile

        T_front, T_rear, fade = _run_thermal_brake_model(
            v_profile, ds, p, ambient_temp_c
        )

    raw["disc_temp_front"] = T_front
    raw["disc_temp_rear"] = T_rear
    raw["brake_fade_factor"] = fade
    return raw


# ---------------------------------------------------------------------------
# Standing start solver
# ---------------------------------------------------------------------------

def _run_standing_start(
    p, x, y, n, ds, s, radius, mu,
    launch_rpm, wheelspin_limit,
    fuel_per_km, temp_ini, p_tyre_cold,
    torque_map_rpm, torque_map_nm,
) -> dict:
    """Standing start: clutch ramp + GGV forward/backward."""
    g = 9.81
    rho = 1.225
    CLUTCH_RAMP_DIST = 30.0

    v_profile    = np.zeros(n)
    a_long       = np.zeros(n)
    a_lat        = np.zeros(n)
    gear_profile = np.ones(n, dtype=int)
    rpm_profile  = np.zeros(n)
    temp_tyre    = np.ones(n) * temp_ini
    fuel_acum    = np.zeros(n)

    v_profile[0]    = 0.0
    gear_profile[0] = 1
    rpm_profile[0]  = launch_rpm
    launch_dist_accum = 0.0

    for i in range(1, n):
        v_prev  = v_profile[i - 1]
        gear    = _select_gear_optimal(max(v_prev, 0.5), p)
        gear_profile[i] = gear

        rpm = max(_get_rpm(v_prev, gear, p), launch_rpm if v_prev < 5.0 else 0)
        rpm_profile[i - 1] = rpm

        if torque_map_rpm:
            T_engine = _torque_curve_interp(rpm, torque_map_rpm, torque_map_nm, p.rpm_max)
        else:
            T_engine = _torque_curve(rpm, p)

        ratio_total  = p.gear_ratios[gear - 1] * p.final_drive
        F_traction_e = T_engine * ratio_total / p.r_wheel
        F_drag       = 0.5 * rho * p.Cx * p.A_front * v_prev ** 2
        F_downforce  = 0.5 * rho * abs(p.Cl) * p.A_front * v_prev ** 2

        # Dynamic mass (fuel_acum[i-1] is the provisional forward-pass
        # estimate; the time-integration loop recomputes it exactly)
        m_fuel_initial = p.initial_fuel_l * p.fuel_density
        fuel_burned_kg = fuel_acum[i - 1] * p.fuel_density
        m_cur = p.m + max(m_fuel_initial - fuel_burned_kg, 0.0)

        F_normal     = m_cur * g + F_downforce

        if launch_dist_accum < CLUTCH_RAMP_DIST:
            clutch_factor = launch_dist_accum / CLUTCH_RAMP_DIST
            slip_limit    = wheelspin_limit * (1.0 - clutch_factor) + 0.05
            F_traction    = min(F_traction_e, mu * F_normal * (1.0 - slip_limit))
        else:
            a_lat_cur   = v_prev ** 2 / max(radius[i], 1.0)
            F_lat_used  = m_cur * a_lat_cur
            F_trac_grip = np.sqrt(max((mu * F_normal) ** 2 - F_lat_used ** 2, 0.0))
            F_traction  = min(F_traction_e, F_trac_grip)

        launch_dist_accum += ds[i]
        a = (F_traction - F_drag) / m_cur
        a_long[i - 1] = a

        v_lat_max = np.sqrt(mu * g * radius[i])
        if ds[i] > 0:
            v_possible   = np.sqrt(max(0.0, v_prev ** 2 + 2 * a * ds[i]))
            v_profile[i] = min(v_possible, v_lat_max, p.speed_limit)
        else:
            v_profile[i] = min(v_prev, p.speed_limit)


        a_combined   = np.sqrt(a ** 2 + (v_prev ** 2 / max(radius[i], 1.0)) ** 2)
        T_ideal      = 25.0 + 100.0 * min(a_combined / (2.0 * g), 1.0)
        dt_step      = ds[i] / max(v_profile[i], 0.1)
        temp_tyre[i] = temp_tyre[i - 1] + (dt_step / 50.0) * (T_ideal - temp_tyre[i - 1])

        # Provisional fuel from BSFC x delivered power (forward-pass
        # estimate used by the dynamic-mass terms above)
        P_engine = max(F_traction, 0.0) * v_prev
        fuel_acum[i] = fuel_acum[i - 1] + _fuel_step(
            P_engine, dt_step, p.bsfc, p.fuel_density
        )

    # Forward loop writes [i-1]; fill last element explicitly
    a_long[n - 1]      = a_long[n - 2]
    rpm_profile[n - 1] = _get_rpm(v_profile[n - 1], gear_profile[n - 1], p)

    for i in reversed(range(n - 1)):
        v_next      = v_profile[i + 1]
        a_lat_next  = v_next ** 2 / max(radius[i + 1], 1.0)

        # Dynamic mass for backward pass
        m_fuel_initial = p.initial_fuel_l * p.fuel_density
        fuel_burned_kg = fuel_acum[i + 1] * p.fuel_density
        m_cur_bw = p.m + max(m_fuel_initial - fuel_burned_kg, 0.0)

        F_downforce_next = 0.5 * rho * abs(p.Cl) * p.A_front * v_next ** 2
        F_normal_next    = m_cur_bw * g + F_downforce_next
        a_decel_max = min(
            np.sqrt(max(0.0, (mu * F_normal_next / m_cur_bw) ** 2 - a_lat_next ** 2)),
            p.max_decel,
            _bias_limited_decel(p, mu, m_cur_bw, F_normal_next),
        )
        if ds[i + 1] > 0:
            v_profile[i] = min(v_profile[i], np.sqrt(v_next ** 2 + 2 * a_decel_max * ds[i + 1]))

    time_profile = np.zeros(n)
    m_fuel_initial = p.initial_fuel_l * p.fuel_density

    for i in range(n):
        a_lat[i] = v_profile[i] ** 2 / max(radius[i], 1.0)
        if i > 0 and v_profile[i] > 0:
            dt = ds[i] / v_profile[i]
            time_profile[i] = time_profile[i - 1] + dt

            # Authoritative fuel: delivered power reconstructed from the
            # final speed profile (zero in braking/coasting zones)
            v_prev_t = v_profile[i - 1]
            a_actual = ((v_profile[i] ** 2 - v_prev_t ** 2) / (2.0 * ds[i])
                        if ds[i] > 0 else 0.0)
            m_cur_t = p.m + max(m_fuel_initial - fuel_acum[i - 1] * p.fuel_density, 0.0)
            F_drag_t = 0.5 * rho * p.Cx * p.A_front * v_prev_t ** 2
            F_engine = m_cur_t * a_actual + F_drag_t
            P_engine = min(max(F_engine, 0.0) * max(v_prev_t, 0.0), p.P_max)
            fuel_acum[i] = fuel_acum[i - 1] + _fuel_step(
                P_engine, dt, p.bsfc, p.fuel_density
            )

    p_tyre_hot = p_tyre_cold + 0.012 * np.maximum(temp_tyre - 25.0, 0.0)

    return {
        "time_profile": time_profile,
        "v_profile":    v_profile,
        "a_long":       a_long,
        "a_lat":        a_lat,
        "gear_profile": gear_profile,
        "rpm_profile":  rpm_profile,
        "temp_tyre":    temp_tyre,
        "tyre_pressure":p_tyre_hot,
        "fuel_acum":    fuel_acum,
    }


# ---------------------------------------------------------------------------
# Public entry point: run_simulation
# ---------------------------------------------------------------------------

def run_simulation(
    config: SimulationConfig,
    vehicle_params: VehicleParams,
    circuit,
    save_csv: bool = True,
    out_path: Optional[str] = None,
) -> SimulationResult:
    """
    Main simulation entry point.

    Applies VehicleSetup to VehicleParams, selects solver based on
    SimulationMode, and returns a SimulationResult with all telemetry
    channels and KPIs.
    """
    t0 = _time.perf_counter()
    logger.info(f"[SIM] {config.describe()}")

    params_eff = apply_setup_to_params(vehicle_params, config.setup)
    p = _build_flat_params(params_eff)

    torque_map_rpm = params_eff.engine.torque_curve_rpm
    torque_map_nm  = params_eff.engine.torque_curve_nm

    x, y, n, ds, s, radius = _compute_track_geometry(circuit)

    mu          = params_eff.tire.friction_coefficient
    temp_ini    = config.track_temperature_c + 5.0
    p_tyre_cold = config.setup.tyre_pressure_avg_front
    wheelbase   = params_eff.mass_geometry.wheelbase

    if config.is_qualifying() or config.is_thermal():
        v0 = 10.0
    elif config.is_flying_lap():
        v0 = config.v_entry_kmh / 3.6
    else:
        v0 = 0.0

    if config.is_standing_start():
        raw = _run_standing_start(
            p=p, x=x, y=y, n=n, ds=ds, s=s, radius=radius,
            mu=mu, launch_rpm=config.launch_rpm,
            wheelspin_limit=config.wheelspin_limit_slip,
            fuel_per_km=p.fuel_per_km, temp_ini=temp_ini,
            p_tyre_cold=p_tyre_cold,
            torque_map_rpm=torque_map_rpm,
            torque_map_nm=torque_map_nm,
        )
    elif config.is_thermal():
        raw = _run_endurance_thermal(
            p=p, x=x, y=y, n=n, ds=ds, s=s, radius=radius,
            mu=mu, v0=v0, temp_ini=temp_ini,
            p_tyre_cold=p_tyre_cold,
            torque_map_rpm=torque_map_rpm,
            torque_map_nm=torque_map_nm,
            ambient_temp_c=config.ambient_temp_c,
            thermal_iterations=config.thermal_iterations,
        )
    else:
        raw = _run_ggv_solver(
            p=p, x=x, y=y, n=n, ds=ds, s=s, radius=radius,
            mu=mu, v0=v0, fuel_per_km=p.fuel_per_km,
            temp_ini=temp_ini, p_tyre_cold=p_tyre_cold,
            torque_map_rpm=torque_map_rpm,
            torque_map_nm=torque_map_nm,
        )

    lap_time = raw["time_profile"][-1]
    v_ms     = raw["v_profile"]
    a_long   = raw["a_long"]

    throttle, brake = _driver_inputs_from_accel(a_long, v_ms * 3.6, max_decel=p.max_decel)
    steering = _steering_from_radius(
        radius, v_ms, wheelbase=wheelbase, steering_ratio=15.0
    )

    result = SimulationResult(
        lap_time          = lap_time,
        mode              = config.mode,
        setup_name        = config.setup.setup_name,
        distance          = s,
        time              = raw["time_profile"],
        v_kmh             = v_ms * 3.6,
        ax_long_g         = a_long / 9.81,
        ay_lat_g          = raw["a_lat"] / 9.81,
        throttle_pct      = throttle,
        brake_pct         = brake,
        steering_deg      = steering,
        gear              = raw["gear_profile"],
        rpm               = raw["rpm_profile"],
        radius            = radius,
        temp_tyre_c       = raw["temp_tyre"],
        tyre_pressure_bar = raw["tyre_pressure"],
        fuel_used_l       = raw["fuel_acum"],
        _a_long_ms2       = a_long,
        _a_lat_ms2        = raw["a_lat"],
        disc_temp_front_c = raw.get("disc_temp_front"),
        disc_temp_rear_c  = raw.get("disc_temp_rear"),
        brake_fade_factor = raw.get("brake_fade_factor"),
    )

    elapsed = _time.perf_counter() - t0
    logger.info(
        f"[PERFORMANCE] GGV Solver Concluído em {elapsed:.4f}s. "
        f"Tempo de volta: {lap_time:.2f}s | "
        f"T_Pneu final: {result.final_tyre_temp_c:.1f}C"
    )
    result.log_kpis()

    if save_csv and out_path:
        result.save_csv(out_path)

    return result


# ---------------------------------------------------------------------------
# Legacy entry point
# ---------------------------------------------------------------------------

def run_bicycle_model(
    params_dict: dict,
    circuit,
    config: dict,
    save_csv: bool = True,
    out_path: Optional[str] = None,
) -> dict:
    """
    Legacy entry point — preserved for backwards compatibility with Streamlit app.

    Wraps run_simulation() converting the flat params_dict and config dict
    into structured objects. Returns the legacy dict format unchanged.
    """
    from ..vehicle.parameters import VehicleParams as StructuredVehicleParams
    from .simulation_modes import SimulationConfig, SimulationMode
    from ..vehicle.setup import (
        get_default_setup,
        _TYRE_PRESSURE_MIN,
        _TYRE_PRESSURE_MAX,
    )

    vp = StructuredVehicleParams.from_solver_dict(params_dict)

    mu_override = config.get("coef_aderencia")
    if mu_override is not None:
        vp.tire.friction_coefficient = float(mu_override)

    temp_pneu_ini = config.get("temp_pneu_ini")
    track_temp = config.get("track_temp", 35.0)
    effective_track_temp = (temp_pneu_ini - 5.0) if temp_pneu_ini is not None else track_temp

    mode_str = config.get("mode", "qualifying")
    if mode_str == "standing_start":
        sim_mode = SimulationMode.STANDING_START
    elif mode_str == "endurance_thermal":
        sim_mode = SimulationMode.ENDURANCE_THERMAL
    else:
        sim_mode = SimulationMode.QUALIFYING

    sim_config = SimulationConfig(
        mode=sim_mode,
        setup=get_default_setup(),
        track_temperature_c=effective_track_temp,
        tyre_compound="slick_dry",
        export_driver_inputs=True,
    )
    # Propagate the vehicle's cold tyre pressure into the setup so the
    # pressure input actually reaches the solver (hot-pressure trace and
    # grip scaling via apply_setup).
    p_cold = params_dict.get('P_cold_bar')
    if p_cold is not None:
        sim_config.setup.tyre_pressure = float(
            np.clip(p_cold, _TYRE_PRESSURE_MIN, _TYRE_PRESSURE_MAX)
        )
    if sim_mode == SimulationMode.STANDING_START:
        sim_config.launch_rpm = float(config.get("launch_rpm", 1500.0))
        sim_config.wheelspin_limit_slip = float(config.get("wheelspin_limit", 0.15))
    elif sim_mode == SimulationMode.ENDURANCE_THERMAL:
        sim_config.ambient_temp_c = float(config.get("ambient_temp_c", 25.0))
        sim_config.thermal_iterations = int(config.get("thermal_iterations", 3))

    result = run_simulation(
        config=sim_config,
        vehicle_params=vp,
        circuit=circuit,
        save_csv=save_csv,
        out_path=out_path,
    )

    legacy = {
        "lap_time":  result.lap_time,
        "distance":  result.distance,
        "v_profile": result.v_kmh / 3.6,
        "a_long":    result._a_long_ms2,
        "a_lat":     result._a_lat_ms2,
        "gear":      result.gear,
        "rpm":       result.rpm,
        "radius":    result.radius,
        "time":      result.time,
        "temp_pneu": result.temp_tyre_c,
        "consumo":   result.fuel_used_l,
        "pressao_pneu": result.tyre_pressure_bar,
        "throttle_pct": result.throttle_pct,
        "brake_pct":    result.brake_pct,
        "steering_deg": result.steering_deg,
    }
    if result.disc_temp_front_c is not None:
        legacy["disc_temp_front"] = result.disc_temp_front_c
        legacy["disc_temp_rear"] = result.disc_temp_rear_c
        legacy["brake_fade_factor"] = result.brake_fade_factor
    return legacy
