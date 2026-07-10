"""
Script para validar e visualizar os circuitos criados.
"""

import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np

from src.tracks.hdf5 import CircuitHDF5Reader


def validate_and_visualize(hdf5_file: str):
    """Valida e visualiza um arquivo HDF5 de circuito."""
    
    reader = CircuitHDF5Reader(hdf5_file)
    circuit, metadata = reader.read_circuit()
    
    # Validações
    print(f"\nValidando: {metadata['name']}")
    print("-" * 50)
    
    # 1. Verificar fechamento do circuito
    start_point = np.array([circuit.centerline_x[0], circuit.centerline_y[0]])
    end_point = np.array([circuit.centerline_x[-1], circuit.centerline_y[-1]])
    gap = np.linalg.norm(end_point - start_point)
    
    print(f"Gap início-fim: {gap:.2f} m")
    if gap < 50:  # Tolerância de 50m
        print("  ✓ Circuito fechado corretamente")
    else:
        print(f"  ⚠ Circuito pode não estar fechado (gap = {gap:.2f}m)")
    
    # 2. Verificar comprimento
    print(f"Comprimento: {metadata['length']:.2f} m ({metadata['length']/1000:.3f} km)")
    
    # 3. Verificar largura
    print(f"Largura média: {metadata['average_width']:.2f} m")
    print(f"Largura mín/máx: {circuit.track_width.min():.2f} / {circuit.track_width.max():.2f} m")
    
    # 4. Verificar continuidade
    dx = np.diff(circuit.centerline_x)
    dy = np.diff(circuit.centerline_y)
    distances = np.sqrt(dx**2 + dy**2)
    max_gap = distances.max()
    
    print(f"Maior espaçamento entre pontos: {max_gap:.2f} m")
    if max_gap < 100:
        print("  ✓ Continuidade adequada")
    else:
        print(f"  ⚠ Possível descontinuidade (max gap = {max_gap:.2f}m)")
    
    # Visualização
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
    
    # Plot 1: Vista geral do circuito
    ax1.plot(circuit.left_boundary_x, circuit.left_boundary_y,
             'r-', linewidth=2, label='Limite esquerdo', alpha=0.8)
    ax1.plot(circuit.right_boundary_x, circuit.right_boundary_y,
             'b-', linewidth=2, label='Limite direito', alpha=0.8)
    ax1.plot(circuit.centerline_x, circuit.centerline_y,
             'k--', linewidth=1, label='Linha central', alpha=0.5)
    
    # Marcar início
    ax1.plot(circuit.centerline_x[0], circuit.centerline_y[0],
             'go', markersize=12, label='Início/Fim', zorder=5)
    
    ax1.set_xlabel('X [m]', fontsize=12)
    ax1.set_ylabel('Y [m]', fontsize=12)
    ax1.set_title(f'{metadata["name"]}\n{metadata["length"]/1000:.3f} km',
                  fontsize=14, fontweight='bold')
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)
    ax1.set_aspect('equal', 'box')
    
    # Plot 2: Perfil de largura
    s = np.linspace(0, metadata['length'], len(circuit.track_width))
    ax2.plot(s/1000, circuit.track_width, 'b-', linewidth=2)
    ax2.fill_between(s/1000, 0, circuit.track_width, alpha=0.3)
    ax2.set_xlabel('Distância [km]', fontsize=12)
    ax2.set_ylabel('Largura da pista [m]', fontsize=12)
    ax2.set_title('Perfil de Largura', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Salvar figura
    output_file = Path(hdf5_file).stem + '.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✓ Visualização salva em: {output_file}")
    
    plt.show()


def validate_all_circuits(tracks_dir: str = "./tracks"):
    """Valida todos os circuitos no diretório."""
    
    tracks_path = Path(tracks_dir)
    hdf5_files = list(tracks_path.glob("*.hdf5"))
    
    if not hdf5_files:
        print(f"Nenhum arquivo HDF5 encontrado em {tracks_dir}")
        return
    
    print(f"\nEncontrados {len(hdf5_files)} circuitos para validar\n")
    
    for hdf5_file in sorted(hdf5_files):
        try:
            validate_and_visualize(str(hdf5_file))
        except Exception as e:
            print(f"Erro ao validar {hdf5_file.name}: {e}")


if __name__ == "__main__":
    # Validar todos os circuitos
    validate_all_circuits()
    
    # Ou validar circuito específico
    # validate_and_visualize("./tracks/interlagos.hdf5")