"""
Telemetry analysis and math channels for lap time simulation.

Implements standard math channels for driver performance analysis (like G-Sum,
Coasting, Brake Speed) and telemetry exporting according to SARU Dynamics standards.

Author: Lap Time Simulator Team
Date: 2026-06-06
"""
import numpy as np
import pandas as pd
from .lap_time_solver import SimulationResult
from ..analysis.brake_lockup import geometry_from_params, lockup_margins
from ..analysis.handling_balance import (
    geometry_from_params as balance_geometry_from_params,
    handling_balance,
)


class SimulationTelemetry:
    """
    Standard analysis and export utility for simulation results.
    Computes math channels and driver trace indicators.
    """

    def __init__(self, result: SimulationResult, params: dict | None = None) -> None:
        """
        Initialize the telemetry analyzer with a SimulationResult.

        Args:
            result: The completed SimulationResult.
            params: Optional flat solver params. When given, per-axle brake
                lockup-margin channels are added (driver-training, no-ABS risk).
        """
        self.result = result
        self.params = params
        self.df = result.to_dataframe()
        self._add_math_channels()
        if params is not None:
            self._add_lockup_channels(params)
            self._add_balance_channels(params)

    def _add_math_channels(self) -> None:
        """Add standard SARU math channels for racecar data analysis."""
        # 1. G-Sum (Combined Acceleration in g)
        self.df['g_sum'] = np.sqrt(self.df['ax_long_g']**2 + self.df['ay_lat_g']**2)

        # 2. Coasting Channel (1.0 if throttle and brake are both zero, else 0.0)
        # We consider a 5% threshold to represent driver coasting between pedals
        self.df['coasting'] = np.where(
            (self.df['throttle_pct'] < 5.0) & (self.df['brake_pct'] < 5.0),
            1.0,
            0.0
        )

        # 3. Brake Speed (%/s) — time derivative of brake pedal position
        time_vals = self.df['lap_time_s'].values
        self.df['brake_speed'] = np.gradient(self.df['brake_pct'].values, time_vals)

        # 4. Long G derivative (Jerk in g/s)
        self.df['jerk_long'] = np.gradient(self.df['ax_long_g'].values, time_vals)

    def _add_lockup_channels(self, params: dict) -> None:
        """Add per-axle brake lockup-margin channels (no-ABS driver training)."""
        a_long = self.result._a_long_ms2
        if a_long is None:
            a_long = self.df['ax_long_g'].values * 9.81
        v_ms = self.result.v_kmh / 3.6
        ch = lockup_margins(v_ms, a_long, geometry_from_params(params))
        self.df['brake_lockup_front'] = ch.front_margin
        self.df['brake_lockup_rear'] = ch.rear_margin
        self.df['brake_lockup_slip'] = ch.slip_estimate

    def _add_balance_channels(self, params: dict) -> None:
        """Add per-axle grip-utilisation and under/oversteer-balance channels."""
        a_lat = self.result._a_lat_ms2
        if a_lat is None:
            a_lat = self.df['ay_lat_g'].values * 9.81
        v_ms = self.result.v_kmh / 3.6
        ch = handling_balance(a_lat, v_ms, balance_geometry_from_params(params))
        self.df['balance_front_util'] = ch.front_utilisation
        self.df['balance_rear_util'] = ch.rear_utilisation
        self.df['handling_balance'] = ch.balance

    def get_metrics(self) -> dict[str, float]:
        """
        Compute aggregate telemetry analysis KPIs.

        Returns:
            Dict containing percentage of coasting, max combined Gs,
            and max brake application speed.
        """
        # Coasting percentage of the lap
        coasting_pct = float(np.mean(self.df['coasting']) * 100.0)
        
        # Max G-Sum
        max_g_sum = float(np.max(self.df['g_sum']))
        
        # Max Brake Speed (rate of application)
        max_brake_apply_speed = float(np.max(self.df['brake_speed']))
        
        return {
            "coasting_pct": coasting_pct,
            "max_g_sum": max_g_sum,
            "max_brake_speed": max_brake_apply_speed,
        }

    def save_to_csv(self, filepath: str) -> None:
        """
        Save telemetry DataFrame (including math channels) to a CSV file.

        Args:
            filepath: Path where CSV will be written.
        """
        self.df.to_csv(filepath, index=False)