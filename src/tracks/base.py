from dataclasses import dataclass
import numpy as np

@dataclass
class CircuitData:
    name: str
    centerline_x: np.ndarray
    centerline_y: np.ndarray
    left_boundary_x: np.ndarray
    left_boundary_y: np.ndarray
    right_boundary_x: np.ndarray
    right_boundary_y: np.ndarray
    track_width: np.ndarray
    coordinate_system: str = "Local Cartesian (m)"
