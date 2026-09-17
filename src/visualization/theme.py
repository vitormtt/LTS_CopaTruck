"""
Shared Plotly styling for the LTS Copa Truck dashboard.

Keeps every chart consistent with the app's dark motorsport theme
(.streamlit/config.toml). Import PLOT and the named colors instead of
hardcoding ``color="royalblue"`` in each component.

Palette is HSL-derived (see .streamlit/config.toml):
- accent  28 90% 55%  -> #f28a1f  (primary trace / "sim")
- neutral bg 220 15% 8% / surface 220 12% 12%
"""
from __future__ import annotations

from typing import Any, Dict

import plotly.graph_objects as go
import plotly.io as pio

# --- Semantic trace colors (HSL-consistent) ---
ACCENT = "#f28a1f"        # primary / simulated lap        (28 90% 55%)
REFERENCE = "#9aa0ad"     # real reference / secondary      (220 8% 64%)
POSITIVE = "#3fb970"      # gain / accel / good             (145 50% 49%)
NEGATIVE = "#e5544b"      # loss / braking / warning        (4 75% 60%)
LATERAL = "#4aa3df"       # lateral channel                 (205 70% 58%)
NEUTRAL = "#6b7280"       # gridlines, zero refs, muted      (220 9% 46%)
HIGHLIGHT = "#c77dff"     # tertiary (rpm/gear overlays)    (275 100% 74%)
EDGE_WHITE = "#e6e8ee"    # track edges / high-contrast line (220 15% 92%)

# Sequential scale for speed/g heatmaps (slow -> fast reads dark -> accent).
# Diverging RdYlGn kept only where "good/bad" polarity is the message.
SEQUENTIAL = "Turbo"
DIVERGING = "RdYlGn"

_BG = "rgba(0,0,0,0)"       # transparent: inherit Streamlit surface
_GRID = "rgba(150,160,175,0.14)"
_FONT = "#e6e8ee"

# Base layout applied to every figure via fig.update_layout(**PLOT).
PLOT: Dict[str, Any] = {
    "paper_bgcolor": _BG,
    "plot_bgcolor": _BG,
    "font": {"color": _FONT, "family": "Source Sans, sans-serif", "size": 12},
    "xaxis": {"gridcolor": _GRID, "zerolinecolor": _GRID},
    "yaxis": {"gridcolor": _GRID, "zerolinecolor": _GRID},
    "legend": {"bgcolor": _BG},
    "colorway": [ACCENT, REFERENCE, LATERAL, POSITIVE, HIGHLIGHT, NEGATIVE],
    "margin": {"l": 0, "r": 0, "t": 30, "b": 0},
}


def style(fig, **overrides: Any):
    """Apply the shared dark theme to a Plotly figure in place.

    Args:
        fig: A plotly.graph_objects.Figure.
        **overrides: Layout keys to override (e.g. height=280, title=...).

    Returns:
        The same figure, for chaining.
    """
    layout = {**PLOT, **overrides}
    # Merge axis dicts so callers can override title without losing grid.
    for axis in ("xaxis", "yaxis"):
        if axis in overrides and isinstance(overrides[axis], dict):
            layout[axis] = {**PLOT[axis], **overrides[axis]}
    fig.update_layout(**layout)
    return fig


# Register a Plotly template so every go.Figure() inherits the dark theme
# (bg / font / gridlines / colorway) even where the component still calls
# fig.update_layout() directly instead of style().
_TEMPLATE = go.layout.Template(
    layout=dict(
        paper_bgcolor=_BG,
        plot_bgcolor=_BG,
        font=dict(color=_FONT, family="Source Sans, sans-serif", size=12),
        xaxis=dict(gridcolor=_GRID, zerolinecolor=_GRID),
        yaxis=dict(gridcolor=_GRID, zerolinecolor=_GRID),
        colorway=[ACCENT, REFERENCE, LATERAL, POSITIVE, HIGHLIGHT, NEGATIVE],
        legend=dict(bgcolor=_BG),
    )
)
pio.templates["lts_dark"] = _TEMPLATE
pio.templates.default = "plotly_dark+lts_dark"
