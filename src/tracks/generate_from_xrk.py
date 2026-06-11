"""
Gerador de Pista de Cascavel (HDF5) a partir de telemetria real do Perez (.xrk).

Lê os dados de GPS do Felipe Giaffone, projeta em ENU, filtra a melhor volta (Lap 14),
aplica suavização spline cúbica periódica e gera o arquivo HDF5 correspondente.

Usage:
    .venv/bin/python src/tracks/generate_from_xrk.py
"""
import os
import sys
import numpy as np
from scipy.interpolate import splprep, splev

# Adiciona o diretório atual no PATH para importar os módulos locais
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.tracks.circuit import CircuitData, CircuitHDF5Writer
from libxrk import aim_xrk

def main():
    xrk_path = "Perez-data/FG04_04_Cascavel PR_Superpole_a_0440.xrk"
    output_path = "tracks/cascavel.hdf5"
    
    print(f"Lendo telemetria AiM: {xrk_path}")
    log = aim_xrk(xrk_path)
    
    # Lap 14 é a volta rápida (1m19s964)
    # Start: 2354410, End: 2434374 (tempo em ms)
    start_ms = 2354410
    end_ms = 2434374
    
    print("Mesclando canais de telemetria...")
    tbl = log.get_channels_as_table()
    df = tbl.to_pandas()
    
    # Filtrar dados da Lap 14
    lap_df = df[(df['timecodes'] >= start_ms) & (df['timecodes'] <= end_ms)].copy()
    
    # Remover duplicadas ou pontos sem GPS válido
    lap_df = lap_df.dropna(subset=['GPS Latitude', 'GPS Longitude'])
    
    lats = lap_df['GPS Latitude'].values
    lons = lap_df['GPS Longitude'].values
    
    # Projeção ENU (East-North-Up) local
    lat0 = np.radians(lats[0])
    lon0 = np.radians(lons[0])
    R = 6378137.0  # Raio equatorial WGS84
    
    # Cálculo das coordenadas Cartesianas locais
    x_raw = R * np.radians(lons - lons[0]) * np.cos(lat0)
    y_raw = R * np.radians(lats - lats[0])
    
    # Forçar fechamento exato do loop
    x_raw[-1] = x_raw[0]
    y_raw[-1] = y_raw[0]
    
    # Downsample leve para evitar pontos ruidosos consecutivos muito próximos
    # Seleciona pontos espaçados
    step = max(1, len(x_raw) // 200) # ~200 pontos de controle para a Spline
    x_control = x_raw[::step]
    y_control = y_raw[::step]
    
    # Garante fechamento do loop nos pontos de controle
    if not np.allclose([x_control[0], y_control[0]], [x_control[-1], y_control[-1]]):
        x_control = np.append(x_control, x_control[0])
        y_control = np.append(y_control, y_control[0])
        
    print(f"Ajustando Spline Periódica sobre {len(x_control)} pontos de controle...")
    
    # Interpolação por Spline Cúbica Periódica
    tck, _ = splprep([x_control, y_control], s=1.0, k=3, per=True)
    
    # Gerar linha central suavizada com 3000 pontos (~1 ponto por metro)
    n_points = 3000
    u_fine = np.linspace(0, 1, n_points, endpoint=False)
    x, y = splev(u_fine, tck)
    x = np.array(x)
    y = np.array(y)
    
    # Cálculo da largura da pista (Cascavel tem largura média regulamentar de 12 metros)
    track_width = np.full(n_points, 12.0)
    
    # Vetores normais para obter as bordas esquerda e direita
    dx = np.gradient(x)
    dy = np.gradient(y)
    norm = np.sqrt(dx ** 2 + dy ** 2) + 1e-12
    nx = -dy / norm
    ny = dx / norm
    hw = track_width / 2.0
    
    left_x = x + nx * hw
    left_y = y + ny * hw
    right_x = x - nx * hw
    right_y = y - ny * hw
    
    # Criar CircuitData
    circuit = CircuitData(
        name="Cascavel — Autódromo Zilmar Beux (Telemetry GPS extraction)",
        centerline_x=x,
        centerline_y=y,
        left_boundary_x=left_x,
        left_boundary_y=left_y,
        right_boundary_x=right_x,
        right_boundary_y=right_y,
        track_width=track_width,
        coordinate_system="local_ENU"
    )
    
    # Gravar HDF5
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    writer = CircuitHDF5Writer(output_path)
    writer.write_circuit(circuit)
    
    # Cálculo do comprimento
    ds = np.sqrt(np.diff(x)**2 + np.diff(y)**2)
    total_length = np.sum(ds)
    
    print(f"Pista gerada com sucesso em: {output_path}")
    print(f"  Nome: {circuit.name}")
    # Nota: O último ponto fecha com o primeiro, então o comprimento é a soma dos segmentos
    print(f"  Comprimento da linha de corrida: {total_length:.2f} m")
    print(f"  Número de pontos: {n_points}")

if __name__ == "__main__":
    main()
