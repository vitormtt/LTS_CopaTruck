"""
Cálculo de curvatura ao longo do traçado do circuito.
"""
import numpy as np


def compute_curvature(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Calcula a curvatura kappa [1/m] ao longo de uma trajetória 2D (x, y)."""
    dx = np.gradient(x)
    dy = np.gradient(y)
    d2x = np.gradient(dx)
    d2y = np.gradient(dy)
    num = np.abs(dx * d2y - dy * d2x)
    den = (dx**2 + dy**2) ** 1.5
    den = np.where(den < 1e-9, 1e-9, den)
    return num / den


def compute_radius(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Calcula o raio de curvatura R [m] ao longo da trajetória."""
    k = compute_curvature(x, y)
    return np.where(k > 1e-6, 1.0 / k, 1e6)


__all__ = ["compute_curvature", "compute_radius"]
