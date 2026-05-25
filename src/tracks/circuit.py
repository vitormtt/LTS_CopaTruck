import h5py
import numpy as np
from typing import Tuple, Dict
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CircuitData:
    """Classe para armazenar dados do circuito."""
    name: str
    centerline_x: np.ndarray
    centerline_y: np.ndarray
    left_boundary_x: np.ndarray
    left_boundary_y: np.ndarray
    right_boundary_x: np.ndarray
    right_boundary_y: np.ndarray
    track_width: np.ndarray
    coordinate_system: str = "UTM"


class CircuitHDF5Writer:
    """Classe para escrever dados de circuito em formato HDF5."""
    
    def __init__(self, filepath: str):
        """
        Inicializa o escritor de arquivo HDF5.
        
        Args:
            filepath: Caminho do arquivo HDF5 a ser criado
        """
        self.filepath = filepath
    
    def write_circuit(self, circuit: CircuitData) -> None:
        """
        Escreve os dados do circuito no arquivo HDF5.
        
        Args:
            circuit: Objeto CircuitData contendo os dados do circuito
        """
        with h5py.File(self.filepath, 'w') as hdf:
            # Metadata
            meta_grp = hdf.create_group('metadata')
            meta_grp.attrs['name'] = circuit.name
            meta_grp.attrs['length'] = self._calculate_length(
                circuit.centerline_x, circuit.centerline_y
            )
            meta_grp.attrs['coordinate_system'] = circuit.coordinate_system
            meta_grp.attrs['date_created'] = datetime.now().isoformat()
            
            # Centerline
            centerline_grp = hdf.create_group('centerline')
            centerline_grp.create_dataset('x', data=circuit.centerline_x, 
                                         compression='gzip', compression_opts=9)
            centerline_grp.create_dataset('y', data=circuit.centerline_y, 
                                         compression='gzip', compression_opts=9)
            
            # Distância acumulada ao longo da linha central
            s = self._calculate_cumulative_distance(
                circuit.centerline_x, circuit.centerline_y
            )
            centerline_grp.create_dataset('s', data=s, 
                                         compression='gzip', compression_opts=9)
            
            # Boundaries
            boundaries_grp = hdf.create_group('boundaries')
            
            left_grp = boundaries_grp.create_group('left')
            left_grp.create_dataset('x', data=circuit.left_boundary_x, 
                                   compression='gzip', compression_opts=9)
            left_grp.create_dataset('y', data=circuit.left_boundary_y, 
                                   compression='gzip', compression_opts=9)
            
            right_grp = boundaries_grp.create_group('right')
            right_grp.create_dataset('x', data=circuit.right_boundary_x, 
                                    compression='gzip', compression_opts=9)
            right_grp.create_dataset('y', data=circuit.right_boundary_y, 
                                    compression='gzip', compression_opts=9)
            
            # Track width
            width_grp = hdf.create_group('track_width')
            width_grp.create_dataset('width', data=circuit.track_width, 
                                    compression='gzip', compression_opts=9)
    
    @staticmethod
    def _calculate_length(x: np.ndarray, y: np.ndarray) -> float:
        """
        Calcula o comprimento total do circuito.
        
        Args:
            x: Coordenadas x
            y: Coordenadas y
            
        Returns:
            Comprimento total em metros
        """
        dx = np.diff(x)
        dy = np.diff(y)
        return float(np.sum(np.sqrt(dx**2 + dy**2)))
    
    @staticmethod
    def _calculate_cumulative_distance(x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """
        Calcula a distância acumulada ao longo da trajetória.
        
        Args:
            x: Coordenadas x
            y: Coordenadas y
            
        Returns:
            Array com distâncias acumuladas
        """
        dx = np.diff(x)
        dy = np.diff(y)
        segment_lengths = np.sqrt(dx**2 + dy**2)
        return np.concatenate(([0], np.cumsum(segment_lengths)))


class CircuitHDF5Reader:
    """Classe para ler dados de circuito em formato HDF5."""
    
    def __init__(self, filepath: str):
        """
        Inicializa o leitor de arquivo HDF5.
        
        Args:
            filepath: Caminho do arquivo HDF5 a ser lido
        """
        self.filepath = filepath
    
    def read_circuit(self) -> Tuple[CircuitData, Dict]:
        """
        Lê os dados do circuito do arquivo HDF5.
        
        Returns:
            Tupla contendo (CircuitData, metadata_dict)
        """
        with h5py.File(self.filepath, 'r') as hdf:
            # Metadata
            metadata = {
                'name': hdf['metadata'].attrs['name'],
                'length': hdf['metadata'].attrs['length'],
                'coordinate_system': hdf['metadata'].attrs['coordinate_system'],
                'date_created': hdf['metadata'].attrs['date_created']
            }
            
            # Carregar dados
            circuit = CircuitData(
                name=metadata['name'],
                centerline_x=hdf['centerline/x'][:],
                centerline_y=hdf['centerline/y'][:],
                left_boundary_x=hdf['boundaries/left/x'][:],
                left_boundary_y=hdf['boundaries/left/y'][:],
                right_boundary_x=hdf['boundaries/right/x'][:],
                right_boundary_y=hdf['boundaries/right/y'][:],
                track_width=hdf['track_width/width'][:],
                coordinate_system=metadata['coordinate_system']
            )
            
            return circuit, metadata


# Exemplo de uso
if __name__ == "__main__":
    # Dados de exemplo (substituir por dados reais do circuito)
    # Para Interlagos, você precisaria obter coordenadas reais
    theta = np.linspace(0, 2*np.pi, 1000)
    radius = 1000.0  # metros
    
    # Simulação de linha central
    centerline_x = radius * np.cos(theta)
    centerline_y = radius * np.sin(theta)
    
    # Largura de pista típica de ~12-15m
    track_width = np.full_like(centerline_x, 12.0)
    
    # Calcular limites (simplificado)
    normals_x = -np.sin(theta)
    normals_y = np.cos(theta)
    
    left_x = centerline_x + normals_x * track_width / 2
    left_y = centerline_y + normals_y * track_width / 2
    right_x = centerline_x - normals_x * track_width / 2
    right_y = centerline_y - normals_y * track_width / 2
    
    # Criar objeto de circuito
    circuit = CircuitData(
        name="Interlagos",
        centerline_x=centerline_x,
        centerline_y=centerline_y,
        left_boundary_x=left_x,
        left_boundary_y=left_y,
        right_boundary_x=right_x,
        right_boundary_y=right_y,
        track_width=track_width
    )
    
    # Salvar
    writer = CircuitHDF5Writer("interlagos.hdf5")
    writer.write_circuit(circuit)
    
    # Ler
    reader = CircuitHDF5Reader("interlagos.hdf5")
    loaded_circuit, metadata = reader.read_circuit()
    
    print(f"Circuito: {metadata['name']}")
    print(f"Comprimento: {metadata['length']:.2f} m")