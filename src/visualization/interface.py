"""
LapTimeSimulator — Streamlit Interface (Modular Router)

Run from project root:
    streamlit run src/visualization/interface.py
"""
import sys
from pathlib import Path
import streamlit as st

# Ensure root directory is in python path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.visualization.components import (
    init_session_state,
    parametros_veiculo_page,
    pista_page,
    simulacao_page,
    resultados_page,
    compare_page,
    optimization_page
)

# Routing dictionary
PAGES = {
    "🚗 Parameters":    parametros_veiculo_page,
    "🗺️ Track":         pista_page,
    "▶️ Simulation":    simulacao_page,
    "🏁 Results":       resultados_page,
    "📊 Compare":       compare_page,
    "🔧 Optimization":  optimization_page,
}

# App-wide layout configuration
st.set_page_config(
    page_title="LapTimeSimulator — Copa Truck / GT3",
    layout="wide",
    page_icon="🏁"
)

# Initialize Session State
init_session_state()

# Sidebar navigation menu
st.sidebar.title("🏁 LapTimeSimulator")
st.sidebar.caption("Copa Truck | Porsche GT3 Cup")
page = st.sidebar.radio("Navigate:", list(PAGES.keys()))

# Execute selected page
PAGES[page]()
