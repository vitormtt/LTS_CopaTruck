"""
Aerodynamics subsystem for vehicle dynamics.

Calculates drag and lift (downforce) forces based on vehicle speed,
aerodynamic coefficients, frontal area, and air density.

Author: Lap Time Simulator Team
Date: 2026-06-06
"""
import numpy as np


class Aerodynamics:
    """
    Standard aerodynamics model representing drag and lift/downforce forces.
    """

    def __init__(
        self,
        drag_coefficient: float,
        frontal_area: float,
        lift_coefficient: float,
        air_density: float = 1.225
    ) -> None:
        """
        Initialize the aerodynamics subsystem.

        Args:
            drag_coefficient: Drag coefficient Cd [-]
            frontal_area: Frontal area [m²]
            lift_coefficient: Lift coefficient Cl [-] (negative for downforce)
            air_density: Density of air [kg/m³] (default 1.225)
        """
        self.cd = drag_coefficient
        self.a_front = frontal_area
        self.cl = lift_coefficient
        self.rho = air_density

    def calculate_forces(self, vx: float) -> dict[str, float]:
        """
        Calculate aerodynamic drag and lift forces at a given speed.

        Args:
            vx: Longitudinal vehicle speed [m/s]

        Returns:
            Dict containing 'drag' (positive backwards, in N), 'lift' (in N),
            and 'downforce' (positive downwards, in N).
        """
        # Dynamic pressure
        q = 0.5 * self.rho * (vx ** 2)
        drag = q * self.cd * self.a_front
        lift = q * self.cl * self.a_front
        
        # Downforce is defined as negative lift (positive downwards force)
        downforce = -lift if self.cl < 0 else 0.0

        return {
            'drag': drag,
            'lift': lift,
            'downforce': downforce
        }

    def __repr__(self) -> str:
        return (
            f"Aerodynamics(Cd={self.cd:.3f}, A_front={self.a_front:.2f} m², "
            f"Cl={self.cl:.3f}, air_density={self.rho:.3f} kg/m³)"
        )
