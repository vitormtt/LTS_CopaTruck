"""
Vehicle parameters module for lap time simulation.

Defines all vehicle parameters required for dynamic simulation,
starting with bicycle model (2DOF) and prepared for expansion to higher-fidelity
models (3DOF, 9DOF, 14DOF).

CHANGELOG:
    2026-03-10 — Split track_width into track_width_front / track_width_rear
                   (required for lateral load transfer computation).
                 — to_solver_dict() now exports k_roll, track_width (avg),
                   Pacejka coefficients, shift_time, abs_slip_target.
                 — from_solver_dict() updated to map new fields.

All parameters use SI units.

Author: Lap Time Simulator Team
References:
    Rajamani, R. (2012). Vehicle Dynamics and Control, 2nd ed. Springer.
    Pacejka, H.B. (2012). Tyre and Vehicle Dynamics, 3rd ed. Butterworth-Heinemann.
    Gillespie, T.D. (1992). Fundamentals of Vehicle Dynamics. SAE International.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
import json


@dataclass
class VehicleMassGeometry:
    """
    Mass and geometry parameters for vehicle dynamics.

    track_width_front and track_width_rear are kept separate to allow
    correct lateral load transfer (delta_Fz) computation in 3DOF+ roll models.
    The solver uses track_width_avg as a backward-compatible scalar.

    References: Rajamani (2012), Pacejka (2012).
    """
    mass: float              # Total vehicle mass [kg]
    lf: float                # Distance from CG to front axle [m]
    lr: float                # Distance from CG to rear axle [m]
    wheelbase: float         # Total wheelbase = lf + lr [m]
    track_width_front: float  # Front track width [m]
    track_width_rear: float  # Rear track width [m]
    cg_height: float         # CG height above ground [m]
    Iz: float                # Yaw moment of inertia [kg·m²]
    Ix: float = 0.0          # Roll moment of inertia [kg·m²] (3DOF+)
    Iy: float = 0.0          # Pitch moment of inertia [kg·m²] (future)

    @property
    def track_width_avg(self) -> float:
        """Average track width [m] — used by 2DOF solver for roll transfer."""
        return (self.track_width_front + self.track_width_rear) / 2.0

    @property
    def weight_distribution_front(self) -> float:
        """Static front weight distribution [-]."""
        return self.lr / self.wheelbase

    @property
    def weight_distribution_rear(self) -> float:
        """Static rear weight distribution [-]."""
        return self.lf / self.wheelbase


@dataclass
class TireParams:
    """
    Tire parameters for lateral and longitudinal force generation.

    For 2DOF: linear tire model (Cf, Cr, mu).
    For future: Pacejka Magic Formula coefficients (B, C, D, E).
    References: Pacejka (2012) — Magic Formula.
    """
    # Linear tire model (2DOF)
    cornering_stiffness_front: float  # Front axle cornering stiffness [N/rad]
    cornering_stiffness_rear: float   # Rear axle cornering stiffness [N/rad]
    friction_coefficient: float       # Peak friction coefficient mu [-]
    wheel_radius: float               # Effective rolling radius [m]

    # Pacejka Magic Formula coefficients (nonlinear models)
    pacejka_B: float = 10.0   # Stiffness factor [-]
    pacejka_C: float = 1.3    # Shape factor [-]
    pacejka_D: float = 1.0    # Peak factor [-]
    pacejka_E: float = 0.97   # Curvature factor [-]

    # Cold tyre pressure (passed to ThermalPacejkaTire)
    cold_pressure_bar: float = 1.8  # Cold tyre pressure [bar]

    # Individual cold tyre pressures [psi]
    cold_pressure_lf_psi: float = 26.1
    cold_pressure_fr_psi: float = 26.1
    cold_pressure_lr_psi: float = 26.1
    cold_pressure_rr_psi: float = 26.1

    # Thermal model (future tire temperature simulation)
    thermal_capacity: float = 0.0      # Tire thermal capacity [J/K]
    thermal_conductivity: float = 0.0  # Thermal conductivity [W/(m·K)]

    def __post_init__(self):
        # Synchronize psi values if loading a legacy preset that only has cold_pressure_bar
        if self.cold_pressure_bar != 1.8 and self.cold_pressure_lf_psi == 26.1:
            psi_val = self.cold_pressure_bar * 14.5038
            self.cold_pressure_lf_psi = psi_val
            self.cold_pressure_fr_psi = psi_val
            self.cold_pressure_lr_psi = psi_val
            self.cold_pressure_rr_psi = psi_val


@dataclass
class AeroParams:
    """
    Aerodynamic parameters for drag and downforce.

    Downforce affects normal loads and the friction circle radius.
    References: Katz, J. (1995). Race Car Aerodynamics. Bentley Publishers.
    """
    drag_coefficient: float   # Cd [-]
    frontal_area: float       # Frontal area [m²]
    lift_coefficient: float   # Cl [-] (negative = downforce)
    air_density: float = 1.225  # Air density [kg/m³] at sea level, 15°C


@dataclass
class EngineParams:
    """
    Engine parameters for powertrain simulation.

    For 2DOF: simplified max power/torque.
    For future: full torque curve interpolation, thermal limits.
    References: Guzzella & Sciarretta (2013). Vehicle Propulsion Systems. Springer.
    """
    max_power: float           # Maximum power [W]
    max_torque: float          # Maximum torque [N·m]
    rpm_max: float             # Maximum RPM [rev/min]
    rpm_idle: float            # Idle RPM [rev/min]
    rpm_redline: float = 0.0   # Redline RPM (if different from max) [rev/min]

    # Brake-specific fuel consumption at high load [g/kWh]
    # Typical modern heavy-duty racing diesel: 195-215 (Heywood 2018)
    bsfc_g_per_kwh: float = 210.0

    # Torque curve (for nonlinear powertrain models)
    torque_curve_rpm: List[float] = field(default_factory=list)  # [rev/min]
    torque_curve_nm: List[float] = field(default_factory=list)   # [N·m]

    # Thermal limits
    max_coolant_temp: float = 110.0  # [°C]
    max_oil_temp: float = 130.0      # [°C]

    def __post_init__(self):
        # Force lists if None was loaded
        if self.torque_curve_rpm is None:
            self.torque_curve_rpm = []
        if self.torque_curve_nm is None:
            self.torque_curve_nm = []

        if len(self.torque_curve_rpm) != len(self.torque_curve_nm):
            raise ValueError(
                f"torque_curve_rpm length ({len(self.torque_curve_rpm)}) "
                f"!= torque_curve_nm length ({len(self.torque_curve_nm)})"
            )
        if any(b <= a for a, b in zip(self.torque_curve_rpm,
                                      self.torque_curve_rpm[1:])):
            raise ValueError("torque_curve_rpm must be strictly increasing")

        if len(self.torque_curve_rpm) == 0:
            is_truck = (self.rpm_max < 3500.0) or (self.max_torque > 1500.0)
            
            if is_truck:
                # Flat racing diesel torque plateau
                rpm_torque_max = self.rpm_max * 0.5  # e.g., 1300 RPM
                rpm_power_max = self.rpm_max * 0.8   # e.g., 2100 RPM
                
                self.torque_curve_rpm = [
                    float(self.rpm_idle),
                    float(rpm_torque_max),
                    float(rpm_power_max),
                    float(self.rpm_max * 0.95),
                    float(self.rpm_max)
                ]
                self.torque_curve_nm = [
                    float(self.max_torque * 0.4), # 40% torque at idle
                    float(self.max_torque),       # peak torque (2800-3350 Nm)
                    float(self.max_torque * 0.95),# 95% torque at peak power (2100 RPM)
                    float(self.max_torque * 0.8), # 80% torque at 2470 RPM
                    float(self.max_torque * 0.6)  # 60% torque at redline
                ]
            else:
                # High-revving racecar (petrol engine)
                rpm_torque_max = self.rpm_max * 0.75 # e.g., 6000-6500 RPM
                self.torque_curve_rpm = [
                    float(self.rpm_idle),
                    float(rpm_torque_max * 0.6),
                    float(rpm_torque_max),
                    float(self.rpm_max * 0.9),
                    float(self.rpm_max)
                ]
                self.torque_curve_nm = [
                    float(self.max_torque * 0.5),
                    float(self.max_torque * 0.85),
                    float(self.max_torque),
                    float(self.max_torque * 0.95),
                    float(self.max_torque * 0.8)
                ]



@dataclass
class TransmissionParams:
    """
    Transmission parameters for gear ratio and shift strategy.

    References: Gillespie (1992). Fundamentals of Vehicle Dynamics. SAE.
    """
    num_gears: int               # Number of forward gears [-]
    gear_ratios: List[float]     # Gear ratios per gear [-]
    final_drive_ratio: float     # Final drive ratio [-]

    shift_time: float = 0.3             # Shift duration [s]
    upshift_rpm: float = 0.0            # RPM threshold for upshift [rev/min]
    downshift_rpm: float = 0.0          # RPM threshold for downshift [rev/min]
    transmission_efficiency: float = 0.95  # Drivetrain efficiency [-]

    def __post_init__(self):
        if len(self.gear_ratios) != self.num_gears:
            raise ValueError(
                f"gear_ratios length ({len(self.gear_ratios)}) "
                f"!= num_gears ({self.num_gears})"
            )


@dataclass
class BrakeParams:
    """
    Brake system parameters for deceleration limits.

    References: Limpert, R. (1999). Brake Design and Safety. SAE International.
    """
    max_brake_force: float     # Maximum total brake force [N]
    brake_balance: float       # Front brake bias [%] (e.g., 52 = 52% front)
    max_deceleration: float    # Physical limit [m/s²]
    brake_response_time: float = 0.1  # Actuator delay [s]

    abs_enabled: bool = False
    abs_slip_target: float = 0.15  # Target slip ratio for ABS [-]

    # Fraction of dissipated kinetic energy absorbed by the discs
    # (remainder goes to engine braking, drag and tyre scrub)
    disc_thermal_efficiency: float = 0.90  # [-]

    # Disc thermal model (ENDURANCE_THERMAL mode) — defaults sized for a
    # ~5 t race truck with vented cast-iron discs (Limpert 1999)
    disc_mass_kg: float = 30.0                  # Per-disc mass [kg]
    disc_specific_heat_j_per_kgk: float = 460.0  # Grey cast iron cp [J/(kg·K)]
    disc_convection_w_per_m2k: float = 60.0      # Base convection h0 [W/(m²·K)]
    disc_area_m2: float = 0.35                   # Cooling area per disc [m²]
    disc_initial_temp_c: float = 60.0            # Disc temperature at lap start [°C]

    # Pad fade band: friction degrades linearly from fade_onset to
    # fade_full, bottoming out at fade_min_factor of the cold capacity
    fade_onset_temp_c: float = 450.0
    fade_full_temp_c: float = 800.0
    fade_min_factor: float = 0.5


@dataclass
class VehicleParams:
    """
    Complete vehicle parameter set for lap time simulation.

    Combines all subsystem parameters into a single structured object
    used by the solver, driver model, and optimisation routines.
    """
    # Core subsystems
    mass_geometry: VehicleMassGeometry
    tire: TireParams
    aero: AeroParams
    engine: EngineParams
    transmission: TransmissionParams
    brake: BrakeParams

    # Roll stiffness (ARB) [Nm/rad]
    k_roll: float = 230_000.0
    k_roll_front: float = 115_000.0
    k_roll_rear: float = 115_000.0

    # Fuel model
    # fuel_consumption_l_per_km is DEPRECATED as a solver input: fuel is
    # now computed dynamically from BSFC x instantaneous power x dt. The
    # field is kept for backward compatibility of serialized presets and
    # as a reporting reference only.
    fuel_consumption_l_per_km: float = 1.5   # [L/km] legacy, output-only
    initial_fuel_l: float = 100.0            # [L] initial fuel load
    fuel_density_kg_per_l: float = 0.85      # [kg/L] diesel

    # Metadata
    name: str = "Unnamed Vehicle"
    manufacturer: str = ""
    year: int = 0
    category: str = "Truck"  # Truck, Formula, etc.

    def to_dict(self) -> Dict:
        """Convert to nested dictionary for JSON serialisation or session_state."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'VehicleParams':
        """Load from nested dictionary (e.g., from JSON or session_state)."""
        mg = data['mass_geometry']
        # Back-compat: if only 'track_width' present, duplicate to front/rear
        if 'track_width' in mg and 'track_width_front' not in mg:
            mg['track_width_front'] = mg.pop('track_width')
            mg['track_width_rear'] = mg['track_width_front']
        tire_data = dict(data['tire'])
        if 'cold_pressure_lf_psi' not in tire_data:
            bar_val = tire_data.get('cold_pressure_bar', 1.8)
            tire_data['cold_pressure_lf_psi'] = bar_val * 14.5038
            tire_data['cold_pressure_fr_psi'] = bar_val * 14.5038
            tire_data['cold_pressure_lr_psi'] = bar_val * 14.5038
            tire_data['cold_pressure_rr_psi'] = bar_val * 14.5038
        return cls(
            mass_geometry=VehicleMassGeometry(**mg),
            tire=TireParams(**tire_data),
            aero=AeroParams(**data['aero']),
            engine=EngineParams(**data['engine']),
            transmission=TransmissionParams(**data['transmission']),
            brake=BrakeParams(**data['brake']),
            k_roll=data.get('k_roll', 230_000.0),
            k_roll_front=data.get('k_roll_front', 115_000.0),
            k_roll_rear=data.get('k_roll_rear', 115_000.0),
            fuel_consumption_l_per_km=data.get('fuel_consumption_l_per_km', 1.5),
            initial_fuel_l=data.get('initial_fuel_l', 100.0),
            fuel_density_kg_per_l=data.get('fuel_density_kg_per_l', 0.85),
            name=data.get('name', 'Unnamed Vehicle'),
            manufacturer=data.get('manufacturer', ''),
            year=data.get('year', 0),
            category=data.get('category', 'Truck')
        )

    def save_to_json(self, filepath: str) -> None:
        """Persist vehicle parameters to JSON file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load_from_json(cls, filepath: str) -> 'VehicleParams':
        """Load vehicle parameters from JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)

    def to_solver_dict(self) -> Dict:
        """
        Flat dictionary compatible with run_bicycle_model() interface.

        Maps the structured dataclass hierarchy to the flat keys expected
        by build_modular_truck_from_dict() in lap_time_solver.py.
        Includes all fields used by the current solver implementation.
        """
        mg = self.mass_geometry
        return {
            # --- Mass / geometry ---
            'm': mg.mass,
            'lf': mg.lf,
            'lr': mg.lr,
            'h_cg': mg.cg_height,
            'Iz': mg.Iz,
            'track_width': mg.track_width_avg,   # solver expects scalar
            'track_width_front': mg.track_width_front,
            'track_width_rear': mg.track_width_rear,

            # --- Roll stiffness (ARB) — front/rear split ---
            'k_roll': self.k_roll,
            'k_roll_front': self.k_roll_front,
            'k_roll_rear': self.k_roll_rear,

            # --- Tires ---
            'Cf': self.tire.cornering_stiffness_front,
            'Cr': self.tire.cornering_stiffness_rear,
            'mu': self.tire.friction_coefficient,
            'r_wheel': self.tire.wheel_radius,
            # Pacejka coefficients (used by ThermalPacejkaTire)
            'pacejka_B': self.tire.pacejka_B,
            'pacejka_C': self.tire.pacejka_C,
            'pacejka_D': self.tire.pacejka_D,
            'pacejka_E': self.tire.pacejka_E,
            'P_cold_bar': self.tire.cold_pressure_bar,
            'P_cold_lf_psi': self.tire.cold_pressure_lf_psi,
            'P_cold_fr_psi': self.tire.cold_pressure_fr_psi,
            'P_cold_lr_psi': self.tire.cold_pressure_lr_psi,
            'P_cold_rr_psi': self.tire.cold_pressure_rr_psi,

            # --- Engine ---
            'P_max': self.engine.max_power,
            'T_max': self.engine.max_torque,
            'rpm_max': self.engine.rpm_max,
            'rpm_idle': self.engine.rpm_idle,
            'torque_curve_rpm': self.engine.torque_curve_rpm,
            'torque_curve_nm': self.engine.torque_curve_nm,

            # --- Transmission ---
            'n_gears': self.transmission.num_gears,
            'gear_ratios': self.transmission.gear_ratios,
            'final_drive': self.transmission.final_drive_ratio,
            'shift_time': self.transmission.shift_time,
            'driveline_eff': self.transmission.transmission_efficiency,
            'upshift_rpm': self.transmission.upshift_rpm,
            'downshift_rpm': self.transmission.downshift_rpm,

            # --- Brakes ---
            'max_decel': self.brake.max_deceleration,
            'brake_balance': self.brake.brake_balance,
            'max_brake_force': self.brake.max_brake_force,
            'abs_slip_target': self.brake.abs_slip_target,
            'abs_enabled': self.brake.abs_enabled,
            'brake_response_time': self.brake.brake_response_time,
            'disc_thermal_efficiency': self.brake.disc_thermal_efficiency,
            'disc_mass_kg': self.brake.disc_mass_kg,
            'disc_specific_heat': self.brake.disc_specific_heat_j_per_kgk,
            'disc_convection': self.brake.disc_convection_w_per_m2k,
            'disc_area_m2': self.brake.disc_area_m2,
            'disc_initial_temp_c': self.brake.disc_initial_temp_c,
            'fade_onset_temp_c': self.brake.fade_onset_temp_c,
            'fade_full_temp_c': self.brake.fade_full_temp_c,
            'fade_min_factor': self.brake.fade_min_factor,

            # --- Aerodynamics ---
            'Cx': self.aero.drag_coefficient,
            'A_front': self.aero.frontal_area,
            'Cl': self.aero.lift_coefficient,

            # --- Fuel model ---
            'fuel_per_km': self.fuel_consumption_l_per_km,  # legacy, unused by solver
            'initial_fuel_l': self.initial_fuel_l,
            'bsfc': self.engine.bsfc_g_per_kwh,
            'fuel_density': self.fuel_density_kg_per_l,
        }

    @classmethod
    def from_solver_dict(cls, data: Dict) -> 'VehicleParams':
        """
        Create VehicleParams from flat solver dictionary.

        Supports both split track_width_front/rear and legacy single track_width.
        """
        lf = data.get('lf', 2.1)
        lr = data.get('lr', 2.3)
        wheelbase = lf + lr

        tw_front = data.get('track_width_front', data.get('track_width', 2.55))
        tw_rear = data.get('track_width_rear', data.get('track_width', 2.55))

        return cls(
            mass_geometry=VehicleMassGeometry(
                mass=data.get('m', 5000.0),
                lf=lf,
                lr=lr,
                wheelbase=wheelbase,
                track_width_front=tw_front,
                track_width_rear=tw_rear,
                cg_height=data.get('h_cg', 1.1),
                Iz=data.get('Iz', 15000.0),
                Ix=data.get('Ix', 2000.0),
                Iy=data.get('Iy', 18000.0),
            ),
            tire=TireParams(
                cornering_stiffness_front=data.get('Cf', 120000.0),
                cornering_stiffness_rear=data.get('Cr', 120000.0),
                friction_coefficient=data.get('mu', 1.1),
                wheel_radius=data.get('r_wheel', 0.65),
                pacejka_B=data.get('pacejka_B', 10.0),
                pacejka_C=data.get('pacejka_C', 1.3),
                pacejka_D=data.get('pacejka_D', 1.0),
                pacejka_E=data.get('pacejka_E', 0.97),
                cold_pressure_bar=data.get('P_cold_bar', 1.8),
                cold_pressure_lf_psi=data.get('P_cold_lf_psi', data.get('P_cold_bar', 1.8) * 14.5038),
                cold_pressure_fr_psi=data.get('P_cold_fr_psi', data.get('P_cold_bar', 1.8) * 14.5038),
                cold_pressure_lr_psi=data.get('P_cold_lr_psi', data.get('P_cold_bar', 1.8) * 14.5038),
                cold_pressure_rr_psi=data.get('P_cold_rr_psi', data.get('P_cold_bar', 1.8) * 14.5038),
            ),
            aero=AeroParams(
                drag_coefficient=data.get('Cx', 0.85),
                frontal_area=data.get('A_front', 8.7),
                lift_coefficient=data.get('Cl', 0.0),
            ),
            engine=EngineParams(
                max_power=data.get('P_max', 600000.0),
                max_torque=data.get('T_max', 3700.0),
                rpm_max=data.get('rpm_max', 2800.0),
                rpm_idle=data.get('rpm_idle', 800.0),
                bsfc_g_per_kwh=data.get('bsfc', 210.0),
                torque_curve_rpm=data.get('torque_curve_rpm', []),
                torque_curve_nm=data.get('torque_curve_nm', []),
            ),
            transmission=TransmissionParams(
                num_gears=data.get('n_gears', 12),
                gear_ratios=data.get('gear_ratios', [14.0, 10.5, 7.8, 5.9, 4.5, 3.5,
                                                     2.7, 2.1, 1.6, 1.25, 1.0, 0.78]),
                final_drive_ratio=data.get('final_drive', 5.33),
                shift_time=data.get('shift_time', 0.3),
                transmission_efficiency=data.get('driveline_eff', 0.95),
                upshift_rpm=data.get('upshift_rpm', 0.0),
                downshift_rpm=data.get('downshift_rpm', 0.0),
            ),
            brake=BrakeParams(
                max_brake_force=data.get('max_brake_force', 50000.0),
                brake_balance=data.get('brake_balance', 58.0),
                max_deceleration=data.get('max_decel', 7.5),
                abs_slip_target=data.get('abs_slip_target', 0.15),
                abs_enabled=data.get('abs_enabled', False),
                brake_response_time=data.get('brake_response_time', 0.1),
                disc_thermal_efficiency=data.get('disc_thermal_efficiency', 0.90),
                disc_mass_kg=data.get('disc_mass_kg', 30.0),
                disc_specific_heat_j_per_kgk=data.get('disc_specific_heat', 460.0),
                disc_convection_w_per_m2k=data.get('disc_convection', 60.0),
                disc_area_m2=data.get('disc_area_m2', 0.35),
                disc_initial_temp_c=data.get('disc_initial_temp_c', 60.0),
                fade_onset_temp_c=data.get('fade_onset_temp_c', 450.0),
                fade_full_temp_c=data.get('fade_full_temp_c', 800.0),
                fade_min_factor=data.get('fade_min_factor', 0.5),
            ),
            k_roll=data.get('k_roll', 230_000.0),
            k_roll_front=data.get('k_roll_front', 115_000.0),
            k_roll_rear=data.get('k_roll_rear', 115_000.0),
            fuel_consumption_l_per_km=data.get('fuel_per_km', 1.5),
            initial_fuel_l=data.get('initial_fuel_l', 100.0),
            fuel_density_kg_per_l=data.get('fuel_density', 0.85),
            name=data.get('name', 'Unnamed Vehicle'),
            manufacturer=data.get('manufacturer', ''),
            year=data.get('year', 0),
            category=data.get('category', 'Truck'),
        )


# ============================================================================
# PRESET VEHICLE MODELS
# ============================================================================

def copa_truck_2dof_default() -> VehicleParams:
    """
    Default Copa Truck parameters for bicycle model (2DOF).

    Based on typical Brazilian Copa Truck racing specifications:
    - Mercedes-Benz Actros racing platform
    - ~850 kW diesel racing engine
    - ~4500 kg racing weight

    References: Copa Truck technical regulations (2024).
    """
    return VehicleParams(
        mass_geometry=VehicleMassGeometry(
            mass=4500.0,
            lf=2.1,
            lr=2.3,
            wheelbase=4.4,
            track_width_front=2.55,
            track_width_rear=2.55,
            cg_height=1.1,
            Iz=15000.0,
            Ix=2000.0,
            Iy=18000.0,
        ),
        tire=TireParams(
            cornering_stiffness_front=135000.0,
            cornering_stiffness_rear=135000.0,
            friction_coefficient=1.62,
            wheel_radius=0.65,
        ),
        aero=AeroParams(
            drag_coefficient=0.80,
            frontal_area=8.7,
            lift_coefficient=0.0,
        ),
        engine=EngineParams(
            max_power=850000.0,
            max_torque=4200.0,
            rpm_max=3500.0,
            rpm_idle=800.0,
        ),
        transmission=TransmissionParams(
            num_gears=12,
            gear_ratios=[14.0, 10.5, 7.8, 5.9, 4.5, 3.5,
                         2.7, 2.1, 1.6, 1.25, 1.0, 0.78],
            final_drive_ratio=4.0,
            shift_time=0.15,
        ),
        brake=BrakeParams(
            max_brake_force=50000.0,
            brake_balance=58.0,
            max_deceleration=9.5,
        ),
        name="Copa Truck Default (2DOF)",
        manufacturer="Mercedes-Benz",
        year=2024,
        category="Truck",
    )



# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def validate_vehicle_params(params: VehicleParams) -> List[str]:
    """
    Validate vehicle parameters for physical consistency.

    Returns:
        List of error messages (empty list if all checks pass).
    """
    errors: List[str] = []

    mg = params.mass_geometry
    if mg.mass <= 0:
        errors.append("Mass must be positive")
    if mg.lf <= 0 or mg.lr <= 0:
        errors.append("lf and lr must be positive")
    if abs(mg.wheelbase - (mg.lf + mg.lr)) > 0.01:
        errors.append(
            f"wheelbase ({mg.wheelbase}) must equal lf + lr ({mg.lf + mg.lr:.3f})")
    if mg.track_width_front <= 0 or mg.track_width_rear <= 0:
        errors.append(
            "track_width_front and track_width_rear must be positive")

    if params.tire.cornering_stiffness_front <= 0 or params.tire.cornering_stiffness_rear <= 0:
        errors.append("Cornering stiffness must be positive")
    if params.tire.friction_coefficient <= 0:
        errors.append("Friction coefficient must be positive")

    if params.engine.max_power <= 0:
        errors.append("Max power must be positive")
    if len(params.transmission.gear_ratios) != params.transmission.num_gears:
        errors.append(
            f"gear_ratios length ({len(params.transmission.gear_ratios)}) "
            f"!= num_gears ({params.transmission.num_gears})"
        )

    if not 0.0 <= params.brake.brake_balance <= 100.0:
        errors.append("brake_balance must be between 0 and 100%")

    return errors
