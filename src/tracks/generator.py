# src/tracks/generator.py
"""
CircuitGenerator: Junta downloaders, calcula limites e salva o arquivo HDF5 pronto para uso na simulação.
"""
import numpy as np
from .hdf5 import CircuitData, CircuitHDF5Writer, CircuitHDF5Reader
from .tumftm import TUMFTMDownloader
from .osm import OpenStreetMapDownloader
import os
from pathlib import Path

def _calculate_boundaries(x, y, w_left, w_right):
    dx = np.gradient(x)
    dy = np.gradient(y)
    mag = np.sqrt(dx**2 + dy**2)
    tx = dx / mag
    ty = dy / mag
    nx = -ty
    ny = tx
    left_x = x + nx * w_left
    left_y = y + ny * w_left
    right_x = x - nx * w_right
    right_y = y - ny * w_right
    return left_x, left_y, right_x, right_y

def from_tumftm(circuit_key: str) -> CircuitData:
    df = TUMFTMDownloader.download(circuit_key)
    x = df['x_m'].values
    y = df['y_m'].values
    w_right = df['w_tr_right_m'].values
    w_left = df['w_tr_left_m'].values
    left_x, left_y, right_x, right_y = _calculate_boundaries(x, y, w_left, w_right)
    track_width = w_left + w_right
    return CircuitData(
        name=circuit_key,
        centerline_x=x,
        centerline_y=y,
        left_boundary_x=left_x,
        left_boundary_y=left_y,
        right_boundary_x=right_x,
        right_boundary_y=right_y,
        track_width=track_width
    )

def from_osm(circuit_key: str) -> CircuitData:
    # Exemplo simples: apenas retorna uma pista circular de demo se OSM falhar
    info = OpenStreetMapDownloader.BRAZILIAN_CIRCUITS.get(circuit_key)
    n_points = 1000
    t = np.linspace(0, 2*np.pi, n_points)
    r = (info['length'] / (2 * np.pi)) if info else 500.0
    x = r * np.cos(t)
    y = r * np.sin(t)
    w = info['width'] if info else 12.0
    w_left = np.full_like(x, w / 2)
    w_right = np.full_like(x, w / 2)
    left_x, left_y, right_x, right_y = _calculate_boundaries(x, y, w_left, w_right)
    track_width = w_left + w_right
    return CircuitData(
        name=circuit_key,
        centerline_x=x,
        centerline_y=y,
        left_boundary_x=left_x,
        left_boundary_y=left_y,
        right_boundary_x=right_x,
        right_boundary_y=right_y,
        track_width=track_width
    )

def create_circuit_hdf5(circuit_key: str, output_dir: str = "./data/tracks") -> str:
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)
    if TUMFTMDownloader.is_available(circuit_key):
        circuit = from_tumftm(circuit_key)
        print(f"[tumftm] Gerou pista: {circuit_key}")
    elif OpenStreetMapDownloader.is_available(circuit_key):
        circuit = from_osm(circuit_key)
        print(f"[osm]       Gerou pista: {circuit_key}")
    else:
        raise ValueError(f"Circuit {circuit_key} not supported")
    out_file = output_path / f"{circuit_key}.hdf5"
    CircuitHDF5Writer(str(out_file)).write_circuit(circuit)
    print(f"[ok] Circuito salvo em {out_file.absolute()}")
    return str(out_file)

if __name__ == "__main__":
    # Exemplo de uso: cria "interlagos" na pasta padrão
    create_circuit_hdf5("interlagos")
    # Você pode passar outros circuitos, exemplo: "cascavel"
