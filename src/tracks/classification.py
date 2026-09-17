"""
Classificação de trechos do circuito em retas e curvas (lentas, médias e rápidas).
"""
from typing import Any, Dict, List
import numpy as np

from src.tracks.curvature import compute_radius


def classify_track_segments(x: np.ndarray, y: np.ndarray, s: np.ndarray) -> List[Dict[str, Any]]:
    """Classifica os trechos de pista com base no raio de curvatura local."""
    radius = compute_radius(x, y)
    segments = []
    n = len(s)
    if n == 0:
        return segments

    for i in range(n):
        r = float(radius[i])
        if r > 400.0:
            tipo = "Straight"
        elif r > 150.0:
            tipo = "Fast Corner"
        elif r > 60.0:
            tipo = "Medium Corner"
        else:
            tipo = "Slow Corner"
        segments.append({"s_m": float(s[i]), "radius_m": r, "type": tipo})

    return segments


__all__ = ["classify_track_segments"]
