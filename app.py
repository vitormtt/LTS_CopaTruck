"""
LTS Perez — Lap Time Simulator (Copa Truck)
Ponto de entrada da interface gráfica Streamlit.

Como executar:
    streamlit run app.py
"""
import os
import sys
from pathlib import Path

# Garante que a raiz do projeto e o diretorio src estejam no PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Executa o roteador principal da interface
import src.visualization.interface
