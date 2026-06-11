# src/tracks/hdf5.py
"""
CircuitHDF5Writer e CircuitHDF5Reader - Gravação/leitura de circuitos HDF5 padronizados.
Uso:
  from .hdf5 import CircuitHDF5Writer, CircuitHDF5Reader
"""
import h5py
import numpy as np
from dataclasses import dataclass
from datetime import datetime

@dataclass
class CircuitData:
    """Estrutura padronizada para circuitos"""
    name: str
    centerline_x: np.ndarray
    centerline_y: np.ndarray
    left_boundary_x: np.ndarray
    left_boundary_y: np.ndarray
    right_boundary_x: np.ndarray
    right_boundary_y: np.ndarray
    track_width: np.ndarray
    coordinate_system: str = "Local Cartesian (m)"

class CircuitHDF5Writer:
    def __init__(self, filepath: str):
        self.filepath = filepath

    def write_circuit(self, circuit: CircuitData, extra_attrs: dict = None) -> None:
        """Write circuit to HDF5.

        Args:
            circuit: Standardized circuit data.
            extra_attrs: Optional extra metadata attributes (e.g.
                ``{'grip_mult': 1.1}``) stored in the metadata group.
        """
        with h5py.File(self.filepath, 'w') as hdf:
            meta_grp = hdf.create_group('metadata')
            meta_grp.attrs['name'] = circuit.name
            meta_grp.attrs['length'] = self._calculate_length(circuit.centerline_x, circuit.centerline_y)
            meta_grp.attrs['coordinate_system'] = circuit.coordinate_system
            meta_grp.attrs['date_created'] = datetime.now().isoformat()
            meta_grp.attrs['n_points'] = len(circuit.centerline_x)
            meta_grp.attrs['average_width'] = float(np.mean(circuit.track_width))
            for key, value in (extra_attrs or {}).items():
                meta_grp.attrs[key] = value
            centerline_grp = hdf.create_group('centerline')
            centerline_grp.create_dataset('x', data=circuit.centerline_x, compression='gzip', compression_opts=9)
            centerline_grp.create_dataset('y', data=circuit.centerline_y, compression='gzip', compression_opts=9)
            s = self._calculate_cumulative_distance(circuit.centerline_x, circuit.centerline_y)
            centerline_grp.create_dataset('s', data=s, compression='gzip', compression_opts=9)
            boundaries_grp = hdf.create_group('boundaries')
            left_grp = boundaries_grp.create_group('left')
            left_grp.create_dataset('x', data=circuit.left_boundary_x, compression='gzip', compression_opts=9)
            left_grp.create_dataset('y', data=circuit.left_boundary_y, compression='gzip', compression_opts=9)
            right_grp = boundaries_grp.create_group('right')
            right_grp.create_dataset('x', data=circuit.right_boundary_x, compression='gzip', compression_opts=9)
            right_grp.create_dataset('y', data=circuit.right_boundary_y, compression='gzip', compression_opts=9)
            width_grp = hdf.create_group('track_width')
            width_grp.create_dataset('width', data=circuit.track_width, compression='gzip', compression_opts=9)

    @staticmethod
    def _calculate_length(x, y):
        dx = np.diff(x)
        dy = np.diff(y)
        return float(np.sum(np.sqrt(dx**2 + dy**2)))

    @staticmethod
    def _calculate_cumulative_distance(x, y):
        dx = np.diff(x)
        dy = np.diff(y)
        segment_lengths = np.sqrt(dx**2 + dy**2)
        return np.concatenate(([0], np.cumsum(segment_lengths)))

class CircuitHDF5Reader:
    def __init__(self, filepath: str):
        self.filepath = filepath

    def read_circuit(self):
        with h5py.File(self.filepath, 'r') as hdf:
            metadata = {
                'name': hdf['metadata'].attrs['name'],
                'length': hdf['metadata'].attrs['length'],
                'coordinate_system': hdf['metadata'].attrs['coordinate_system'],
                'date_created': hdf['metadata'].attrs['date_created'],
                'n_points': hdf['metadata'].attrs.get('n_points', 0),
                'average_width': hdf['metadata'].attrs.get('average_width', 0),
                'grip_mult': hdf['metadata'].attrs.get('grip_mult', 1.0),
            }
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
