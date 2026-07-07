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
    driveline_eff: float = 0.95
    shift_time: float = 0.3
    max_decel: float = 7.5
    brake_balance: float = 58.0
    max_brake_force: float = 50000.0
    brake_response_time: float = 0.1
    abs_enabled: bool = False
    abs_slip_target: float = 0.15
    bsfc: float = 210.0
    pacejka_B: float = 10.0
    pacejka_C: float = 1.3
    pacejka_D: float = 1.0
    pacejka_E: float = 0.97
    Cx: float = 0.85
    A_front: float = 8.7
    Cl: float = 0.0
    aero_balance: float = 0.5
    combined_grip_factor: float = 0.9
    k_roll_front: float = 115_000.0
    k_roll_rear: float = 115_000.0
    track_width: float = 1.565
    track_width_front: float = 2.55
    track_width_rear: float = 2.55
    P_cold_lf_psi: float = 26.1
    P_cold_fr_psi: float = 26.1
    P_cold_lr_psi: float = 26.1
    P_cold_rr_psi: float = 26.1
    Iz: float = 0.0
    fuel_per_km: float = 1.5
    speed_limit: float = 999.0
    initial_fuel_l: float = 100.0
    fuel_density: float = 0.85

    def __post_init__(self):
        if self.gear_ratios is None:
            self.gear_ratios = [14.0, 10.5, 7.8, 5.9, 4.5, 3.5, 2.7, 2.1,
                                 1.6, 1.25, 1.0, 0.78]
        self.L = self.lf + self.lr
        if self.Iz <= 0.0:
            # Geometric estimate when the preset does not provide Iz
            self.Iz = self.m * (self.lf**2 + self.lr**2) / 2
        if self.track_width_front <= 0.0:
            self.track_width_front = self.track_width
        if self.track_width_rear <= 0.0:
            self.track_width_rear = self.track_width


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

    # Axle slip-angle channels (steady-state bicycle model, Cf/Cr)
    front_slip_angle_deg: Optional[np.ndarray] = None
    rear_slip_angle_deg: Optional[np.ndarray] = None

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

    @property
    def understeer_margin_deg(self) -> Optional[float]:
        """Mean front-minus-rear slip angle [deg]. Positive = understeer."""
        if self.front_slip_angle_deg is None:
            return None
        return float(np.mean(self.front_slip_angle_deg
                             - self.rear_slip_angle_deg))

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
        if self.front_slip_angle_deg is not None:
            df["front_slip_angle_deg"] = self.front_slip_angle_deg
            df["rear_slip_angle_deg"] = self.rear_slip_angle_deg
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
    # Regulation speed governor: explicit param wins; legacy presets without
    # it fall back to the Copa Truck 200 km/h limit (Truck) or unlimited.
    if getattr(vp, "speed_limit_kmh", 0.0) > 0.0:
        p.speed_limit = vp.speed_limit_kmh / 3.6
    elif vp.category == "Truck" or "truck" in vp.name.lower():
        p.speed_limit = 200.0 / 3.6
    else:
        p.speed_limit = 999.0
    return p



def _driving_line(circuit) -> tuple:
    """Racing-line (x, y) for the circuit, cached on the circuit object.

    Falls back to the centerline when the circuit lacks boundary channels.
    The line depends only on track geometry, so it is computed once and
    reused across the many solver calls of an optimization sweep.
    """
    cached = getattr(circuit, "_racing_line_xy", None)
    if cached is not None:
        return cached

    x, y = circuit.centerline_x, circuit.centerline_y
    have_bounds = all(
        getattr(circuit, attr, None) is not None and len(getattr(circuit, attr)) == len(x)
        for attr in ("left_boundary_x", "left_boundary_y",
                     "right_boundary_x", "right_boundary_y")
    )
    if have_bounds:
        from src.tracks.racing_line import compute_racing_line
        center = np.column_stack([x, y])
        left = np.column_stack([circuit.left_boundary_x, circuit.left_boundary_y])
        right = np.column_stack([circuit.right_boundary_x, circuit.right_boundary_y])
        # Closed loop when the ends nearly meet.
        closed = bool(np.hypot(x[0] - x[-1], y[0] - y[-1]) < 5.0)
        rl = compute_racing_line(center, left, right, closed=closed)
        result = (rl.x, rl.y)
    else:
        result = (np.asarray(x, dtype=float), np.asarray(y, dtype=float))

    try:
        circuit._racing_line_xy = result
    except (AttributeError, TypeError):
        pass  # circuit may be immutable; recompute next call
    return result


def _compute_track_geometry(circuit, path: Optional[tuple] = None) -> tuple:
    """Compute ds, s, radius and signed curvature from a driving line.

    Args:
        circuit: Circuit with centerline (and optionally boundaries).
        path: Optional (x, y) driving line; defaults to the centerline.
    """
    if path is not None:
        x, y = path
    else:
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
    # Signed curvature consistent with the clipped radius (sign = turn
    # direction; magnitude = 1/radius) — used by the yaw-rate model
    kappa = np.sign(curvature) / radius

    return x, y, n, ds, s, radius, kappa


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
    fallback_gear, fallback_force = 1, -1.0
    for gear in range(1, p.n_gears + 1):
        ratio_total = p.gear_ratios[gear - 1] * p.final_drive
        rpm = (v / max(p.r_wheel, 0.01)) * ratio_total * 60.0 / (2 * np.pi)
        if rpm > p.rpm_max:
            continue
        rpm = max(rpm, p.rpm_idle)
        T = _torque_curve(rpm, p)
        F = T * ratio_total / p.r_wheel
        if F > fallback_force:
            fallback_force = F
            fallback_gear = gear
        if rpm_min_opt <= rpm <= rpm_max_opt:
            if F > best_force:
                best_force = F
                best_gear = gear
    if best_force >= 0.0:
        return best_gear
    return fallback_gear


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
    max_decel: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Derive throttle_pct and brake_pct from longitudinal acceleration.

    QSS solver is binary: forward pass = full throttle, backward pass = full
    brake. Throttle is 100% wherever a_long > 0; brake scales linearly with
    deceleration magnitude up to max_decel.
    """
    throttle = np.where(a_long > 0.0, 100.0, 0.0)
    brake    = np.clip((-a_long / np.maximum(max_decel, 1e-6)) * 100.0, 0.0, 100.0)
    return throttle, brake


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
# Physics model constants (named, calibrable)
# ---------------------------------------------------------------------------

_G = 9.81           # [m/s²]
_RHO_AIR = 1.225    # [kg/m³]
# Output sign of the lateral-accel channel: +1 → positive Ay = left turn
# (kappa > 0). Flip to -1.0 if a reference logger uses the opposite mount.
_AY_SIGN = 1.0
# Convergence tolerance for the qualifying flying-lap periodic v0 [m/s].
_QUALI_V0_TOL_MS = 0.3
# Tyre load sensitivity: relative grip loss per unit of relative lateral
# load transfer on an axle (Pacejka 2012, load-sensitivity of mu).
# Calibrated against the validated lap-time windows (Cascavel 76-82 s,
# Interlagos 125-132 s) together with the preset mu/Cx values.
# Tyre load sensitivity — calibrated against real telemetry windows
# (VW 31320: Cascavel 76-82 s, Interlagos 125-132 s), see
# docs/SESSION_LOG_2026-06-11.md. Do not retune without cross-validation.
_S_LOAD = 0.12

# Couple per-wheel hot pressure/temperature into the friction coefficient
# (the "full car" tyre model). Off by default: not yet calibrated against
# real telemetry — see the note inside _axle_grip().
_THERMAL_GRIP_COUPLING = False

# Optimum cold-pressure for the p_factor curve. Copa Truck regulation
# tyres are heavy-truck radials (295/80 R22.5 per the 2024-2026 CBA
# research dossier, docs/COPA_TRUCK_POWERTRAIN_RESEARCH.md) operating
# around 95-125 psi — NOT the ~34 psi passenger-car optimum previously
# hardcoded. The CBA rulebook does not mandate a pressure, so this is an
# operating-range estimate: calibrate with Perez telemetry before
# enabling _THERMAL_GRIP_COUPLING. The quadratic loss factor is rescaled
# to keep the same relative sensitivity over the 10x wider psi range.
_P_OPT_PSI = 110.0
_P_FACTOR_K = 1.5e-5   # was 0.0015 on the ~34 psi car scale

# Fraction of the peak axle lateral force usable as yaw-moment authority
# during direction changes (quasi-transient extension)
_YAW_MOMENT_FACTOR = 0.5
# Reference braking-zone duration for the first-order pedal-response
# model: effective decel = cap * T_ref / (T_ref + t_response/2)
_T_BRAKE_ZONE_REF = 2.5   # [s]
# Threshold-braking margin of a driver without ABS (Limpert 1999)
_NO_ABS_MODULATION = 0.94
# Speed hysteresis below the last upshift point before a downshift is
# allowed (prevents shift limit-cycles when the cut drops the speed)
_DOWNSHIFT_HYST_MS = 2.0   # [m/s]
_ABS_PEAK_SLIP = 0.15           # slip ratio at peak longitudinal force
_ABS_SLIP_SENSITIVITY = 0.5     # efficiency loss per unit slip-target error
_F_NORMAL_FLOOR_FRAC = 0.1      # min F_normal as fraction of m*g (lift floor)
# Tyre thermal model
_T_AMBIENT_TYRE = 25.0   # [degC]
_T_SCALE_TYRE = 100.0    # [degC] rise at 2g combined load above ambient
_TAU_TYRE = 50.0         # [s] thermal time constant


# ---------------------------------------------------------------------------
# Subsystem physics helpers (engine, aero, axle grip, brakes, yaw)
# ---------------------------------------------------------------------------

def _engine_torque(
    rpm: float,
    p: _LegacyVehicleParams,
    torque_map_rpm: list,
    torque_map_nm: list,
) -> float:
    """Engine torque [N·m] at rpm, capped so T*omega never exceeds P_max."""
    if torque_map_rpm:
        T = _torque_curve_interp(rpm, torque_map_rpm, torque_map_nm, p.rpm_max)
    else:
        T = _torque_curve(rpm, p)
    omega = max(rpm, p.rpm_idle) * 2.0 * np.pi / 60.0
    if omega > 0.0:
        T = min(T, p.P_max / omega)
    return T


def _aero_normal_force(p: _LegacyVehicleParams, v: float) -> float:
    """Aerodynamic vertical force [N]. Positive = downforce (Cl < 0)."""
    return -0.5 * _RHO_AIR * p.Cl * p.A_front * v ** 2


def _axle_grip(
    p: _LegacyVehicleParams,
    mu: float,
    m_cur: float,
    v: float,
    a_lat_est: float,
    temp_lf: float = 25.0,
    temp_fr: float = 25.0,
    temp_lr: float = 25.0,
    temp_rr: float = 25.0,
) -> tuple[float, float, float, float, float]:
    """
    Quasi-static axle grip with lateral load transfer and individual tire pressures/temperatures.

    Calculates individual normal forces on the 4 wheels and adjusts the friction coefficient
    at each corner based on hot tire pressure (PSI) and temperature (degC).
    """
    F_aero = _aero_normal_force(p, v)
    # Distribute weight by CG position, and aero downforce by aero_balance (CoP)
    Fz_f_static = (m_cur * _G * p.lr / p.L) + (F_aero * p.aero_balance)
    Fz_r_static = (m_cur * _G * p.lf / p.L) + (F_aero * (1.0 - p.aero_balance))
    
    # Enforce floor limits per axle to prevent singularities
    floor_f = _F_NORMAL_FLOOR_FRAC * m_cur * _G * (p.lr / p.L)
    floor_r = _F_NORMAL_FLOOR_FRAC * m_cur * _G * (p.lf / p.L)
    Fz_f_static = max(Fz_f_static, floor_f)
    Fz_r_static = max(Fz_r_static, floor_r)
    F_normal = Fz_f_static + Fz_r_static

    k_total = max(p.k_roll_front + p.k_roll_rear, 1.0)
    frac_f = p.k_roll_front / k_total
    tw_f = max(p.track_width_front, 0.5)
    tw_r = max(p.track_width_rear, 0.5)

    lat_moment = m_cur * abs(a_lat_est) * p.h_cg
    dfz_f = lat_moment / tw_f * frac_f
    dfz_r = lat_moment / tw_r * (1.0 - frac_f)

    # 4 wheels normal loads. Load is CONSERVED per axle: when the inner
    # wheel lifts (clamped at zero), the outer wheel carries the remaining
    # axle load — never more. Without the complementary assignment the
    # outer wheel got 0.5*Fz + dfz with no upper cap, creating phantom
    # axle load (and grip) that grew with lateral transfer.
    Fz_LF = max(0.5 * Fz_f_static - dfz_f, 0.0)
    Fz_RF = Fz_f_static - Fz_LF
    Fz_LR = max(0.5 * Fz_r_static - dfz_r, 0.0)
    Fz_RR = Fz_r_static - Fz_LR

    # Thermal/pressure -> grip coupling ("full car" tyre model).
    # DISABLED until calibrated against real telemetry (Perez-data .xrk):
    # coupling hot pressure/temperature into mu moved lap times away from
    # the validated telemetry windows (VW 31320: Cascavel 76-82 s,
    # Interlagos 125-132 s) and inverted physical expectations (a narrower
    # track heats tyres faster and gained more from t_factor than it lost
    # to load transfer). Per-wheel temperature/pressure stay live as
    # telemetry channels; re-enable only with cross-validation (Golden
    # Rule 2). _P_OPT_PSI/_P_FACTOR_K are sized for the regulation truck
    # tyre pressure range — see the module constants and the dossier in
    # docs/COPA_TRUCK_POWERTRAIN_RESEARCH.md.
    if _THERMAL_GRIP_COUPLING:
        T_opt = 80.0

        P_hot_lf = p.P_cold_lf_psi + 0.174 * (temp_lf - _T_AMBIENT_TYRE)
        p_factor_lf = max(1.0 - _P_FACTOR_K * (P_hot_lf - _P_OPT_PSI) ** 2, 0.5)
        t_factor_lf = max(1.0 - 0.00005 * (temp_lf - T_opt) ** 2, 0.5)

        P_hot_fr = p.P_cold_fr_psi + 0.174 * (temp_fr - _T_AMBIENT_TYRE)
        p_factor_fr = max(1.0 - _P_FACTOR_K * (P_hot_fr - _P_OPT_PSI) ** 2, 0.5)
        t_factor_fr = max(1.0 - 0.00005 * (temp_fr - T_opt) ** 2, 0.5)

        P_hot_lr = p.P_cold_lr_psi + 0.174 * (temp_lr - _T_AMBIENT_TYRE)
        p_factor_lr = max(1.0 - _P_FACTOR_K * (P_hot_lr - _P_OPT_PSI) ** 2, 0.5)
        t_factor_lr = max(1.0 - 0.00005 * (temp_lr - T_opt) ** 2, 0.5)

        P_hot_rr = p.P_cold_rr_psi + 0.174 * (temp_rr - _T_AMBIENT_TYRE)
        p_factor_rr = max(1.0 - _P_FACTOR_K * (P_hot_rr - _P_OPT_PSI) ** 2, 0.5)
        t_factor_rr = max(1.0 - 0.00005 * (temp_rr - T_opt) ** 2, 0.5)
    else:
        p_factor_lf = t_factor_lf = 1.0
        p_factor_fr = t_factor_fr = 1.0
        p_factor_lr = t_factor_lr = 1.0
        p_factor_rr = t_factor_rr = 1.0

    # Axle-level load sensitivity scaling
    mu_base = mu * p.pacejka_D
    ls_f = 1.0 - _S_LOAD * min(dfz_f / max(Fz_f_static / 2.0, 1.0), 0.95)
    ls_r = 1.0 - _S_LOAD * min(dfz_r / max(Fz_r_static / 2.0, 1.0), 0.95)

    # Individual tire grip coefficients
    mu_LF = mu_base * p_factor_lf * t_factor_lf * ls_f
    mu_RF = mu_base * p_factor_fr * t_factor_fr * ls_f
    mu_LR = mu_base * p_factor_lr * t_factor_lr * ls_r
    mu_RR = mu_base * p_factor_rr * t_factor_rr * ls_r

    # Average/effective axle-level variables (back-compat)
    Fz_f = Fz_LF + Fz_RF
    Fz_r = Fz_LR + Fz_RR
    mu_f = (mu_LF * Fz_LF + mu_RF * Fz_RF) / max(Fz_f, 1.0)
    mu_r = (mu_LR * Fz_LR + mu_RR * Fz_RR) / max(Fz_r, 1.0)

    return mu_f, mu_r, Fz_f, Fz_r, F_normal


def _v_corner_limit(
    p: _LegacyVehicleParams,
    mu_lat: float,
    m_cur: float,
    radius_i: float,
) -> float:
    """
    Cornering speed limit including aerodynamic load.

    Solves m*v²/R <= mu*(m*g + c*v²) with c = -0.5*rho*Cl*A (downforce
    raises the limit, lift lowers it). Falls back to the speed limiter
    when downforce makes the corner aero-unlimited.
    """
    c_aero = -0.5 * _RHO_AIR * p.Cl * p.A_front
    denom = m_cur - mu_lat * c_aero * radius_i
    if denom <= 0.05 * m_cur:
        return p.speed_limit
    return float(np.sqrt(max(mu_lat * m_cur * _G * radius_i / denom, 0.0)))


def _brake_system_cap(
    p: _LegacyVehicleParams,
    mu_total: float,
    m_cur: float,
    F_normal: float,
) -> float:
    """
    Brake-SYSTEM deceleration cap (tyre grip handled separately).

    Combines the system decel limit, the bias/first-axle-lockup limit,
    the ABS / driver-modulation efficiency and a first-order pedal
    response loss (average ramp loss over a reference braking zone).
    """
    cap = min(p.max_decel,
              _bias_limited_decel(p, mu_total, m_cur, F_normal))
    if p.abs_enabled:
        cap *= max(1.0 - _ABS_SLIP_SENSITIVITY
                   * abs(p.abs_slip_target - _ABS_PEAK_SLIP), 0.5)
    else:
        cap *= _NO_ABS_MODULATION
    cap *= _T_BRAKE_ZONE_REF / (_T_BRAKE_ZONE_REF
                                + max(p.brake_response_time, 0.0) / 2.0)
    return cap


def _yaw_speed_cap(
    v_cand: float,
    v_prev: float,
    kappa_i: float,
    kappa_prev: float,
    ds_i: float,
    p: _LegacyVehicleParams,
    mz_avail: float,
) -> float:
    """
    Quasi-transient yaw-rate cap (makes Iz live in the QSS solver).

    Between consecutive points the yaw rate changes from v_prev*k_prev
    to v*k_i over dt = ds/v; the required yaw moment Iz*d(psi_dot)/dt
    may not exceed the available tyre yaw authority. When violated, the
    candidate speed is reduced by bisection.
    """
    if ds_i <= 0.0 or p.Iz <= 0.0:
        return v_cand

    def mz_required(v: float) -> float:
        return p.Iz * v * abs(v * kappa_i - v_prev * kappa_prev) / ds_i

    if mz_required(v_cand) <= mz_avail:
        return v_cand

    lo, hi = 0.0, v_cand
    for _ in range(20):
        mid = 0.5 * (lo + hi)
        if mz_required(mid) <= mz_avail:
            lo = mid
        else:
            hi = mid
    return lo


def _backward_pass(
    v_profile: np.ndarray,
    fuel_acum: np.ndarray,
    p: _LegacyVehicleParams,
    mu: float,
    ds: np.ndarray,
    radius: np.ndarray,
    fade: Optional[np.ndarray] = None,
    temp_LF: Optional[np.ndarray] = None,
    temp_RF: Optional[np.ndarray] = None,
    temp_LR: Optional[np.ndarray] = None,
    temp_RR: Optional[np.ndarray] = None,
) -> None:
    """
    Shared braking (backward) pass — mutates v_profile in place.

    Deceleration at each point is the minimum of the combined tyre-grip
    limit (friction circle on the axle model) and the brake-system cap
    (optionally scaled by a thermal fade factor).
    """
    n = len(v_profile)
    m_fuel_initial = p.initial_fuel_l * p.fuel_density

    for i in reversed(range(n - 1)):
        v_next = v_profile[i + 1]
        a_lat_next = v_next ** 2 / max(radius[i + 1], 1.0)

        fuel_burned_kg = fuel_acum[i + 1] * p.fuel_density
        m_cur = p.m + max(m_fuel_initial - fuel_burned_kg, 0.0)

        t_lf = temp_LF[i + 1] if temp_LF is not None else 25.0
        t_fr = temp_RF[i + 1] if temp_RF is not None else 25.0
        t_lr = temp_LR[i + 1] if temp_LR is not None else 25.0
        t_rr = temp_RR[i + 1] if temp_RR is not None else 25.0

        mu_f, mu_r, Fz_f, Fz_r, F_normal = _axle_grip(
            p, mu, m_cur, v_next, a_lat_next, t_lf, t_fr, t_lr, t_rr
        )
        # All four wheels brake: capacity-weighted total friction
        mu_total = (mu_f * Fz_f + mu_r * Fz_r) / F_normal

        a_grip_pure = mu_total * F_normal / m_cur
        a_grip = np.sqrt(max(a_grip_pure ** 2 - a_lat_next ** 2, 0.0))
        if a_lat_next > 0.1 * a_grip_pure:
            a_grip *= p.combined_grip_factor
        cap = _brake_system_cap(p, mu_total, m_cur, F_normal)
        if fade is not None:
            cap *= fade[i + 1]

        a_decel_max = min(a_grip, cap)
        if ds[i + 1] > 0:
            v_brake_limit = np.sqrt(v_next ** 2 + 2 * a_decel_max * ds[i + 1])
            v_profile[i] = min(v_profile[i], v_brake_limit)


def _finalize_pass(
    v_profile: np.ndarray,
    fuel_acum: np.ndarray,
    p: _LegacyVehicleParams,
    ds: np.ndarray,
    radius: np.ndarray,
) -> dict:
    """
    Shared time-integration pass over the FINAL speed profile.

    Recomputes the authoritative channels so telemetry matches the
    actual lap: time, longitudinal acceleration, gear/RPM, fuel (BSFC x
    delivered power), axle slip angles (linear below the Magic-Formula
    peak) and steady-state bicycle steering
    delta = L/R + alpha_f - alpha_r.
    """
    n = len(v_profile)
    time_profile = np.zeros(n)
    a_long = np.zeros(n)
    a_lat = np.zeros(n)
    gear_profile = np.ones(n, dtype=int)
    rpm_profile = np.zeros(n)
    alpha_f_deg = np.zeros(n)
    alpha_r_deg = np.zeros(n)
    steering_deg = np.zeros(n)
    m_fuel_initial = p.initial_fuel_l * p.fuel_density

    # Slip angle at the Magic-Formula peak (B/C shape the curve)
    alpha_peak = np.tan(np.pi / (2.0 * max(p.pacejka_C, 1.01))) \
        / max(p.pacejka_B, 1.0)
    steering_ratio = 15.0

    for i in range(n):
        v_i = v_profile[i]
        a_lat[i] = v_i ** 2 / max(radius[i], 1.0)
        gear_profile[i] = _select_gear_optimal(max(v_i, 0.5), p)
        rpm_profile[i] = _get_rpm(v_i, gear_profile[i], p)

        m_cur = p.m + max(
            m_fuel_initial - fuel_acum[max(i - 1, 0)] * p.fuel_density, 0.0
        )

        # Axle lateral forces from steady-state moment balance
        F_yf = m_cur * a_lat[i] * p.lr / p.L
        F_yr = m_cur * a_lat[i] * p.lf / p.L
        alpha_f = min(F_yf / max(p.Cf, 1.0), alpha_peak)
        alpha_r = min(F_yr / max(p.Cr, 1.0), alpha_peak)
        alpha_f_deg[i] = np.degrees(alpha_f)
        alpha_r_deg[i] = np.degrees(alpha_r)
        steering_deg[i] = np.degrees(
            p.L / max(radius[i], 1.0) + alpha_f - alpha_r
        ) * steering_ratio

        if i > 0 and v_i > 0:
            dt = ds[i] / v_i
            time_profile[i] = time_profile[i - 1] + dt

            v_prev = v_profile[i - 1]
            a_actual = ((v_i ** 2 - v_prev ** 2) / (2.0 * ds[i])
                        if ds[i] > 0 else 0.0)
            a_long[i] = a_actual

            # Authoritative fuel: delivered power from the final profile
            F_drag = 0.5 * _RHO_AIR * p.Cx * p.A_front * v_prev ** 2
            F_engine = m_cur * a_actual + F_drag
            P_engine = min(max(F_engine, 0.0) * max(v_prev, 0.0), p.P_max)
            fuel_acum[i] = fuel_acum[i - 1] + _fuel_step(
                P_engine, dt, p.bsfc, p.fuel_density
            )

    if n > 1:
        a_long[0] = a_long[1]

    # Dynamic steering damping/smoothing at high speeds / straights (look-ahead)
    smoothed_steering = np.copy(steering_deg)
    for i in range(n):
        v_i = v_profile[i]
        if v_i > 15.0:  # damping active above 54 km/h
            lookahead_m = min(v_i * 0.4, 25.0)  # scales with speed, max 25m
            dist_fwd = 0.0
            idx_fwd = i
            while idx_fwd < n - 1 and dist_fwd < lookahead_m:
                dist_fwd += ds[idx_fwd + 1]
                idx_fwd += 1
            if idx_fwd > i:
                smoothed_steering[i] = np.mean(steering_deg[i : idx_fwd + 1])
    steering_deg = smoothed_steering

    return {
        "time_profile": time_profile,
        "a_long": a_long,
        "a_lat": a_lat,
        "gear_profile": gear_profile,
        "rpm_profile": rpm_profile,
        "front_slip_angle_deg": alpha_f_deg,
        "rear_slip_angle_deg": alpha_r_deg,
        "steering_deg": steering_deg,
    }


# ---------------------------------------------------------------------------
# Core GGV solver
# ---------------------------------------------------------------------------

def _run_ggv_solver(
    p, x, y, n, ds, s, radius, kappa, mu, v0,
    temp_ini, p_tyre_cold,
    torque_map_rpm, torque_map_nm,
    temp_LF_ini: Optional[float] = None,
    temp_RF_ini: Optional[float] = None,
    temp_LR_ini: Optional[float] = None,
    temp_RR_ini: Optional[float] = None,
) -> dict:
    """
    GGV forward + backward pass solver with live subsystems.

    Forward pass: traction limited by the P_max-capped torque curve
    through the driveline (efficiency + shift-time traction cut), by
    the driven REAR axle grip (with longitudinal load transfer helping
    traction) and by the cornering limit including aero load. A
    quasi-transient yaw-rate cap makes Iz effective in chicanes.
    Backward pass and channel finalization are shared helpers.
    """
    v_profile = np.zeros(n)
    temp_LF = np.ones(n) * (temp_LF_ini if temp_LF_ini is not None else temp_ini)
    temp_RF = np.ones(n) * (temp_RF_ini if temp_RF_ini is not None else temp_ini)
    temp_LR = np.ones(n) * (temp_LR_ini if temp_LR_ini is not None else temp_ini)
    temp_RR = np.ones(n) * (temp_RR_ini if temp_RR_ini is not None else temp_ini)
    temp_tyre = np.ones(n) * ((temp_LF[0] + temp_RF[0] + temp_LR[0] + temp_RR[0]) / 4.0)
    fuel_acum = np.zeros(n)
    m_fuel_initial = p.initial_fuel_l * p.fuel_density

    v_profile[0] = v0
    gear_cur = _select_gear_optimal(max(v0, 0.5), p)
    shift_dist_remaining = 0.0
    v_last_upshift = 0.0
    a_long_prev = 0.0

    for i in range(1, n):
        v_prev = v_profile[i - 1]
        if shift_dist_remaining > 0.0:
            gear = gear_cur  # hold gear through the traction cut
        else:
            gear_opt = _select_gear_optimal(max(v_prev, 0.5), p)
            if gear_opt > gear_cur:
                # Upshift interrupts traction for shift_time
                shift_dist_remaining = v_prev * p.shift_time
                v_last_upshift = v_prev
                gear_cur = gear_opt
            elif (gear_opt < gear_cur
                  and v_prev < v_last_upshift - _DOWNSHIFT_HYST_MS):
                gear_cur = gear_opt  # downshift (engine braking, no cut)
            gear = gear_cur

        rpm = _get_rpm(v_prev, gear, p)
        T_engine = _engine_torque(rpm, p, torque_map_rpm, torque_map_nm)

        ratio_total = p.gear_ratios[gear - 1] * p.final_drive
        F_traction = T_engine * ratio_total * p.driveline_eff / p.r_wheel
        if shift_dist_remaining > 0.0:
            # Traction cut for the covered fraction of this step only
            # (avoids inflating the cut on coarse track grids)
            cut_frac = min(shift_dist_remaining / max(ds[i], 1e-9), 1.0)
            F_traction *= (1.0 - cut_frac)
            shift_dist_remaining -= ds[i]
        F_drag = 0.5 * _RHO_AIR * p.Cx * p.A_front * v_prev ** 2

        fuel_burned_kg = fuel_acum[i - 1] * p.fuel_density
        m_cur = p.m + max(m_fuel_initial - fuel_burned_kg, 0.0)

        a_lat_cur = v_prev ** 2 / max(radius[i], 1.0)
        mu_f, mu_r, Fz_f, Fz_r, F_normal = _axle_grip(
            p, mu, m_cur, v_prev, a_lat_cur,
            temp_LF[i - 1], temp_RF[i - 1], temp_LR[i - 1], temp_RR[i - 1]
        )

        # RWD traction: rear axle grip, helped by longitudinal load
        # transfer m*a*h/L (evaluated with the previous step's accel)
        Fz_r_trac = Fz_r + m_cur * max(a_long_prev, 0.0) * p.h_cg / p.L
        F_yr_used = m_cur * a_lat_cur * p.lf / p.L
        F_trac_pure = mu_r * Fz_r_trac
        F_trac_grip = np.sqrt(max(F_trac_pure ** 2 - F_yr_used ** 2, 0.0))
        if F_yr_used > 0.1 * F_trac_pure:
            F_trac_grip *= p.combined_grip_factor
        F_traction = min(F_traction, F_trac_grip)

        a = (F_traction - F_drag) / m_cur
        a_long_prev = a

        v_lat_max = _v_corner_limit(p, min(mu_f, mu_r), m_cur, radius[i])
        if ds[i] > 0:
            v_possible = np.sqrt(max(0.0, v_prev ** 2 + 2 * a * ds[i]))
            v_cand = min(v_possible, v_lat_max, p.speed_limit)
            # Quasi-transient yaw-rate cap (Iz)
            mz_avail = _YAW_MOMENT_FACTOR * (
                mu_f * Fz_f * p.lf + mu_r * Fz_r * p.lr
            )
            v_profile[i] = _yaw_speed_cap(
                v_cand, v_prev, kappa[i], kappa[i - 1], ds[i], p, mz_avail
            )
        else:
            v_profile[i] = min(v_prev, p.speed_limit)

        # Tyre thermal — 4-wheel dynamic load scaled model
        a_drag = F_drag / m_cur
        a_rr = 0.015 * _G
        a_combined = np.sqrt((a + a_drag + a_rr) ** 2 + a_lat_cur ** 2)

        # Calculate individual normal forces on the 4 wheels for work scaling
        Fz_f_static = F_normal * p.lr / p.L
        Fz_r_static = F_normal * p.lf / p.L
        k_total = max(p.k_roll_front + p.k_roll_rear, 1.0)
        frac_f = p.k_roll_front / k_total
        tw_f = max(p.track_width_front, 0.5)
        tw_r = max(p.track_width_rear, 0.5)
        lat_moment = m_cur * abs(a_lat_cur) * p.h_cg
        dfz_f = lat_moment / tw_f * frac_f
        dfz_r = lat_moment / tw_r * (1.0 - frac_f)

        # Per-axle load conservation (see _axle_grip)
        Fz_LF = max(0.5 * Fz_f_static - dfz_f, 0.0)
        Fz_RF = Fz_f_static - Fz_LF
        Fz_LR = max(0.5 * Fz_r_static - dfz_r, 0.0)
        Fz_RR = Fz_r_static - Fz_LR

        Fz_static_f = 0.5 * Fz_f_static
        Fz_static_r = 0.5 * Fz_r_static

        work_lf = a_combined * (Fz_LF / max(Fz_static_f, 1.0))
        work_fr = a_combined * (Fz_RF / max(Fz_static_f, 1.0))
        work_lr = a_combined * (Fz_LR / max(Fz_static_r, 1.0))
        work_rr = a_combined * (Fz_RR / max(Fz_static_r, 1.0))

        T_ideal_lf = temp_ini + _T_SCALE_TYRE * min(work_lf / (2.0 * _G), 1.5)
        T_ideal_fr = temp_ini + _T_SCALE_TYRE * min(work_fr / (2.0 * _G), 1.5)
        T_ideal_lr = temp_ini + _T_SCALE_TYRE * min(work_lr / (2.0 * _G), 1.5)
        T_ideal_rr = temp_ini + _T_SCALE_TYRE * min(work_rr / (2.0 * _G), 1.5)
        
        dt_step = ds[i] / max(v_profile[i], 0.1)
        temp_LF[i] = temp_LF[i - 1] + (dt_step / _TAU_TYRE) * (T_ideal_lf - temp_LF[i - 1])
        temp_RF[i] = temp_RF[i - 1] + (dt_step / _TAU_TYRE) * (T_ideal_fr - temp_RF[i - 1])
        temp_LR[i] = temp_LR[i - 1] + (dt_step / _TAU_TYRE) * (T_ideal_lr - temp_LR[i - 1])
        temp_RR[i] = temp_RR[i - 1] + (dt_step / _TAU_TYRE) * (T_ideal_rr - temp_RR[i - 1])
        
        temp_tyre[i] = (temp_LF[i] + temp_RF[i] + temp_LR[i] + temp_RR[i]) / 4.0

        # Provisional fuel from BSFC x delivered power (forward-pass
        # estimate used by the dynamic-mass terms above)
        P_engine = max(F_traction, 0.0) * v_prev
        fuel_acum[i] = fuel_acum[i - 1] + _fuel_step(
            P_engine, dt_step, p.bsfc, p.fuel_density
        )

    _backward_pass(
        v_profile, fuel_acum, p, mu, ds, radius,
        temp_LF=temp_LF, temp_RF=temp_RF, temp_LR=temp_LR, temp_RR=temp_RR
    )
    channels = _finalize_pass(v_profile, fuel_acum, p, ds, radius)

    p_tyre_hot = p_tyre_cold + 0.012 * np.maximum(temp_tyre - 25.0, 0.0)

    return {
        "v_profile":    v_profile,
        "temp_tyre":    temp_tyre,
        "temp_LF":      temp_LF,
        "temp_RF":      temp_RF,
        "temp_LR":      temp_LR,
        "temp_RR":      temp_RR,
        "tyre_pressure": p_tyre_hot,
        "fuel_acum":    fuel_acum,
        **channels,
    }



# ---------------------------------------------------------------------------
# Standing start solver
# ---------------------------------------------------------------------------

def _run_standing_start(
    p, x, y, n, ds, s, radius, kappa, mu,
    launch_rpm, wheelspin_limit,
    temp_ini, p_tyre_cold,
    torque_map_rpm, torque_map_nm,
) -> dict:
    """Standing start: clutch ramp + GGV forward/backward (live subsystems)."""
    # 30 m clutch-engagement ramp reproduces the validated +~7.6 s gap of a
    # 4.5 t truck standing start vs qualifying (docs/SESSION_LOG_2026-06-11.md).
    CLUTCH_RAMP_DIST = 30.0

    # A launch RPM above the engine's rev limiter would zero the torque
    # (fuel cut) and freeze the vehicle on the start line — clamp it to the
    # usable engine band (SimulationConfig's default of 4500 rpm is a GT
    # value; Copa Truck diesels rev to ~3500).
    launch_rpm = float(np.clip(launch_rpm, p.rpm_idle, p.rpm_max * 0.9))

    v_profile = np.zeros(n)
    temp_LF = np.ones(n) * temp_ini
    temp_RF = np.ones(n) * temp_ini
    temp_LR = np.ones(n) * temp_ini
    temp_RR = np.ones(n) * temp_ini
    temp_tyre = np.ones(n) * temp_ini
    fuel_acum = np.zeros(n)
    m_fuel_initial = p.initial_fuel_l * p.fuel_density

    launch_dist_accum = 0.0
    gear_cur = 1
    shift_dist_remaining = 0.0
    v_last_upshift = 0.0
    a_long_prev = 0.0

    for i in range(1, n):
        v_prev = v_profile[i - 1]
        in_launch = launch_dist_accum < CLUTCH_RAMP_DIST
        if shift_dist_remaining > 0.0 and not in_launch:
            gear = gear_cur  # hold gear through the traction cut
        else:
            gear_opt = _select_gear_optimal(max(v_prev, 0.5), p)
            if gear_opt > gear_cur:
                if not in_launch:
                    shift_dist_remaining = v_prev * p.shift_time
                v_last_upshift = v_prev
                gear_cur = gear_opt
            elif (gear_opt < gear_cur
                  and v_prev < v_last_upshift - _DOWNSHIFT_HYST_MS):
                gear_cur = gear_opt
            gear = gear_cur

        rpm = max(_get_rpm(v_prev, gear, p), launch_rpm if v_prev < 5.0 else 0)
        T_engine = _engine_torque(rpm, p, torque_map_rpm, torque_map_nm)

        ratio_total = p.gear_ratios[gear - 1] * p.final_drive
        F_traction_e = T_engine * ratio_total * p.driveline_eff / p.r_wheel
        if shift_dist_remaining > 0.0 and not in_launch:
            # Traction cut for the covered fraction of this step only
            cut_frac = min(shift_dist_remaining / max(ds[i], 1e-9), 1.0)
            F_traction_e *= (1.0 - cut_frac)
            shift_dist_remaining -= ds[i]
        F_drag = 0.5 * _RHO_AIR * p.Cx * p.A_front * v_prev ** 2

        fuel_burned_kg = fuel_acum[i - 1] * p.fuel_density
        m_cur = p.m + max(m_fuel_initial - fuel_burned_kg, 0.0)

        a_lat_cur = v_prev ** 2 / max(radius[i], 1.0)
        mu_f, mu_r, Fz_f, Fz_r, F_normal = _axle_grip(
            p, mu, m_cur, v_prev, a_lat_cur,
            temp_LF[i - 1], temp_RF[i - 1], temp_LR[i - 1], temp_RR[i - 1]
        )
        Fz_r_trac = Fz_r + m_cur * max(a_long_prev, 0.0) * p.h_cg / p.L

        if launch_dist_accum < CLUTCH_RAMP_DIST:
            clutch_factor = launch_dist_accum / CLUTCH_RAMP_DIST
            slip_limit = wheelspin_limit * (1.0 - clutch_factor) + 0.05
            F_traction = min(
                F_traction_e, mu_r * Fz_r_trac * (1.0 - slip_limit)
            )
        else:
            F_yr_used = m_cur * a_lat_cur * p.lf / p.L
            F_trac_pure = mu_r * Fz_r_trac
            F_trac_grip = np.sqrt(max(F_trac_pure ** 2 - F_yr_used ** 2, 0.0))
            if F_yr_used > 0.1 * F_trac_pure:
                F_trac_grip *= p.combined_grip_factor
            F_traction = min(F_traction_e, F_trac_grip)

        launch_dist_accum += ds[i]
        a = (F_traction - F_drag) / m_cur
        a_long_prev = a

        v_lat_max = _v_corner_limit(p, min(mu_f, mu_r), m_cur, radius[i])
        if ds[i] > 0:
            v_possible = np.sqrt(max(0.0, v_prev ** 2 + 2 * a * ds[i]))
            v_cand = min(v_possible, v_lat_max, p.speed_limit)
            mz_avail = _YAW_MOMENT_FACTOR * (
                mu_f * Fz_f * p.lf + mu_r * Fz_r * p.lr
            )
            v_profile[i] = _yaw_speed_cap(
                v_cand, v_prev, kappa[i], kappa[i - 1], ds[i], p, mz_avail
            )
        else:
            v_profile[i] = min(v_prev, p.speed_limit)

        # Tyre thermal — 4-wheel dynamic load scaled model
        a_drag = F_drag / m_cur
        a_rr = 0.015 * _G
        a_combined = np.sqrt((a + a_drag + a_rr) ** 2 + a_lat_cur ** 2)

        Fz_f_static = F_normal * p.lr / p.L
        Fz_r_static = F_normal * p.lf / p.L
        k_total = max(p.k_roll_front + p.k_roll_rear, 1.0)
        frac_f = p.k_roll_front / k_total
        tw_f = max(p.track_width_front, 0.5)
        tw_r = max(p.track_width_rear, 0.5)
        lat_moment = m_cur * abs(a_lat_cur) * p.h_cg
        dfz_f = lat_moment / tw_f * frac_f
        dfz_r = lat_moment / tw_r * (1.0 - frac_f)

        # Per-axle load conservation (see _axle_grip)
        Fz_LF = max(0.5 * Fz_f_static - dfz_f, 0.0)
        Fz_RF = Fz_f_static - Fz_LF
        Fz_LR = max(0.5 * Fz_r_static - dfz_r, 0.0)
        Fz_RR = Fz_r_static - Fz_LR

        Fz_static_f = 0.5 * Fz_f_static
        Fz_static_r = 0.5 * Fz_r_static

        work_lf = a_combined * (Fz_LF / max(Fz_static_f, 1.0))
        work_fr = a_combined * (Fz_RF / max(Fz_static_f, 1.0))
        work_lr = a_combined * (Fz_LR / max(Fz_static_r, 1.0))
        work_rr = a_combined * (Fz_RR / max(Fz_static_r, 1.0))

        T_ideal_lf = temp_ini + _T_SCALE_TYRE * min(work_lf / (2.0 * _G), 1.5)
        T_ideal_fr = temp_ini + _T_SCALE_TYRE * min(work_fr / (2.0 * _G), 1.5)
        T_ideal_lr = temp_ini + _T_SCALE_TYRE * min(work_lr / (2.0 * _G), 1.5)
        T_ideal_rr = temp_ini + _T_SCALE_TYRE * min(work_rr / (2.0 * _G), 1.5)

        dt_step = ds[i] / max(v_profile[i], 0.1)
        temp_LF[i] = temp_LF[i - 1] + (dt_step / _TAU_TYRE) * (T_ideal_lf - temp_LF[i - 1])
        temp_RF[i] = temp_RF[i - 1] + (dt_step / _TAU_TYRE) * (T_ideal_fr - temp_RF[i - 1])
        temp_LR[i] = temp_LR[i - 1] + (dt_step / _TAU_TYRE) * (T_ideal_lr - temp_LR[i - 1])
        temp_RR[i] = temp_RR[i - 1] + (dt_step / _TAU_TYRE) * (T_ideal_rr - temp_RR[i - 1])

        temp_tyre[i] = (temp_LF[i] + temp_RF[i] + temp_LR[i] + temp_RR[i]) / 4.0

        P_engine = max(F_traction, 0.0) * v_prev
        fuel_acum[i] = fuel_acum[i - 1] + _fuel_step(
            P_engine, dt_step, p.bsfc, p.fuel_density
        )

    _backward_pass(
        v_profile, fuel_acum, p, mu, ds, radius,
        temp_LF=temp_LF, temp_RF=temp_RF, temp_LR=temp_LR, temp_RR=temp_RR
    )
    channels = _finalize_pass(v_profile, fuel_acum, p, ds, radius)
    # Preserve the launch RPM at the start line for telemetry realism
    channels["rpm_profile"][0] = launch_rpm

    p_tyre_hot = p_tyre_cold + 0.012 * np.maximum(temp_tyre - 25.0, 0.0)

    return {
        "v_profile":    v_profile,
        "temp_tyre":    temp_tyre,
        "temp_LF":      temp_LF,
        "temp_RF":      temp_RF,
        "temp_LR":      temp_LR,
        "temp_RR":      temp_RR,
        "tyre_pressure": p_tyre_hot,
        "fuel_acum":    fuel_acum,
        **channels,
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

    driving_path = _driving_line(circuit) if getattr(config, "use_racing_line", False) else None
    x, y, n, ds, s, radius, kappa = _compute_track_geometry(circuit, driving_path)

    mu          = params_eff.tire.friction_coefficient
    temp_ini    = config.track_temperature_c + 5.0
    p_tyre_cold = config.setup.tyre_pressure_avg_front

    if config.is_flying_lap():
        v0 = config.v_entry_kmh / 3.6
    elif config.is_standing_start():
        v0 = 0.0
    else:  # qualifying — seed for the periodic fixed-point below
        v0 = 10.0

    # Tyres still start at ambient state (no thermal pre-lap): the validation
    # windows were calibrated cold, and a thermal warm-up must not be
    # reintroduced without re-validating vs real telemetry. The ENTRY SPEED,
    # however, now uses the flying-lap periodic boundary condition for
    # qualifying (below) instead of the old cold v0 = 10 m/s (~36 km/h).
    if config.is_standing_start():
        raw = _run_standing_start(
            p=p, x=x, y=y, n=n, ds=ds, s=s, radius=radius, kappa=kappa,
            mu=mu, launch_rpm=config.launch_rpm,
            wheelspin_limit=config.wheelspin_limit_slip,
            temp_ini=temp_ini,
            p_tyre_cold=p_tyre_cold,
            torque_map_rpm=torque_map_rpm,
            torque_map_nm=torque_map_nm,
        )
    else:
        def _ggv(v_start: float) -> dict:
            return _run_ggv_solver(
                p=p, x=x, y=y, n=n, ds=ds, s=s, radius=radius, kappa=kappa,
                mu=mu, v0=v_start,
                temp_ini=temp_ini, p_tyre_cold=p_tyre_cold,
                torque_map_rpm=torque_map_rpm,
                torque_map_nm=torque_map_nm,
            )

        raw = _ggv(v0)
        if config.is_qualifying() and getattr(config, "use_flying_lap_start", False):
            # Flying-lap periodic boundary condition: a qualifying lap is a
            # closed loop, so the speed crossing the start/finish line equals
            # the speed leaving it on the identical previous lap. Fixed-point
            # iterate v0 -> v_profile[-1] (a handful of passes converge, as it
            # is the same track point). Removes the unphysical ~36 km/h launch
            # that made sector 1 a slow climb.
            #
            # OFF by default: on the Cascavel anchor it cuts the lap ~4.5 s
            # (80.7 -> 76.2), overshooting the real 1:19.5 pole by ~3.3 s
            # because mu was co-calibrated with the cold slow start (same knot
            # as use_racing_line). Enable only alongside a mu recalibration
            # validated vs .xrk — see SPM P0b.
            for _ in range(5):
                v_end = float(raw["v_profile"][-1])
                if abs(v_end - v0) < _QUALI_V0_TOL_MS:
                    break
                v0 = v_end
                raw = _ggv(v0)

    lap_time = raw["time_profile"][-1]
    v_ms     = raw["v_profile"]
    a_long   = raw["a_long"]

    # Sign the lateral-accel channel by turn direction (kappa > 0 = left).
    # The solver only ever needs |a_lat| (grip is a friction circle), so
    # signing the OUTPUT channel leaves lap time and every grip term
    # untouched — it just makes the G-G diagram bilateral and lets the .xrk
    # overlay compare left vs right corners. Convention: + = left, which
    # matches the Copa Truck AiM loggers (LateralAcc corr +0.93 vs v*yaw).
    a_lat_signed = _AY_SIGN * np.sign(kappa) * np.abs(raw["a_lat"])

    # Calculate instantaneous maximum deceleration capacity at each point for brake_pct
    a_decel_max = np.zeros(n)
    m_fuel_initial = p.initial_fuel_l * p.fuel_density
    for i in range(n):
        v = v_ms[i]
        a_lat = v ** 2 / max(radius[i], 1.0)

        t_lf = raw["temp_LF"][i] if "temp_LF" in raw else 25.0
        t_fr = raw["temp_RF"][i] if "temp_RF" in raw else 25.0
        t_lr = raw["temp_LR"][i] if "temp_LR" in raw else 25.0
        t_rr = raw["temp_RR"][i] if "temp_RR" in raw else 25.0

        fuel_burned_kg = raw["fuel_acum"][i] * p.fuel_density
        m_cur = p.m + max(m_fuel_initial - fuel_burned_kg, 0.0)

        mu_f, mu_r, Fz_f, Fz_r, F_normal = _axle_grip(
            p, mu, m_cur, v, a_lat, t_lf, t_fr, t_lr, t_rr
        )
        mu_total = (mu_f * Fz_f + mu_r * Fz_r) / F_normal
        a_grip_pure = mu_total * F_normal / m_cur
        a_grip = np.sqrt(max(a_grip_pure ** 2 - a_lat ** 2, 0.0))
        if a_lat > 0.1 * a_grip_pure:
            a_grip *= p.combined_grip_factor
        cap = _brake_system_cap(p, mu_total, m_cur, F_normal)
        if raw.get("brake_fade_factor") is not None:
            cap *= raw["brake_fade_factor"][i]

        a_decel_max[i] = min(a_grip, cap)

    throttle, brake = _driver_inputs_from_accel(a_long, v_ms * 3.6, a_decel_max)

    result = SimulationResult(
        lap_time          = lap_time,
        mode              = config.mode,
        setup_name        = config.setup.setup_name,
        distance          = s,
        time              = raw["time_profile"],
        v_kmh             = v_ms * 3.6,
        ax_long_g         = a_long / 9.81,
        ay_lat_g          = a_lat_signed / 9.81,
        throttle_pct      = throttle,
        brake_pct         = brake,
        steering_deg      = raw["steering_deg"],
        gear              = raw["gear_profile"],
        rpm               = raw["rpm_profile"],
        radius            = radius,
        temp_tyre_c       = raw["temp_tyre"],
        tyre_pressure_bar = raw["tyre_pressure"],
        fuel_used_l       = raw["fuel_acum"],
        _a_long_ms2       = a_long,
        _a_lat_ms2        = a_lat_signed,
        front_slip_angle_deg = raw["front_slip_angle_deg"],
        rear_slip_angle_deg  = raw["rear_slip_angle_deg"],
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
    else:
        sim_mode = SimulationMode.QUALIFYING

    sim_config = SimulationConfig(
        mode=sim_mode,
        setup=get_default_setup(),
        track_temperature_c=effective_track_temp,
        tyre_compound="slick_dry",
        export_driver_inputs=True,
        use_racing_line=bool(config.get("use_racing_line", False)),
        use_flying_lap_start=bool(config.get("use_flying_lap_start", False)),
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
    if result.front_slip_angle_deg is not None:
        legacy["front_slip_angle_deg"] = result.front_slip_angle_deg
        legacy["rear_slip_angle_deg"] = result.rear_slip_angle_deg
    return legacy
