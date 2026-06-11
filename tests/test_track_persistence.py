"""
Tests for HDF5 track persistence (UI 'Salvar Pista' flow).
"""
import hashlib
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.tracks.hdf5 import (  # noqa: E402
    CircuitData,
    CircuitHDF5Reader,
    CircuitHDF5Writer,
)

SOURCE_TRACK = ROOT / "tracks" / "cascavel.hdf5"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_modified_track_round_trip(tmp_path) -> None:
    """Width-scaled circuit + grip attr survive a write/read round trip."""
    source_hash_before = _sha256(SOURCE_TRACK)

    circuit, _ = CircuitHDF5Reader(str(SOURCE_TRACK)).read_circuit()

    w_scale = 1.3
    width = circuit.track_width * w_scale
    dx = np.gradient(circuit.centerline_x)
    dy = np.gradient(circuit.centerline_y)
    norm = np.sqrt(dx ** 2 + dy ** 2) + 1e-12
    nx, ny = -dy / norm, dx / norm
    hw = width / 2.0

    modified = CircuitData(
        name="Cascavel Modified",
        centerline_x=circuit.centerline_x.copy(),
        centerline_y=circuit.centerline_y.copy(),
        left_boundary_x=circuit.centerline_x + nx * hw,
        left_boundary_y=circuit.centerline_y + ny * hw,
        right_boundary_x=circuit.centerline_x - nx * hw,
        right_boundary_y=circuit.centerline_y - ny * hw,
        track_width=width,
        coordinate_system=circuit.coordinate_system,
    )

    out_path = tmp_path / "cascavel_modified.hdf5"
    CircuitHDF5Writer(str(out_path)).write_circuit(
        modified, extra_attrs={"grip_mult": 1.15}
    )

    reread, meta = CircuitHDF5Reader(str(out_path)).read_circuit()

    np.testing.assert_allclose(reread.track_width,
                               circuit.track_width * w_scale, rtol=1e-12)
    np.testing.assert_allclose(reread.centerline_x, circuit.centerline_x)
    np.testing.assert_allclose(reread.left_boundary_x, modified.left_boundary_x)
    assert meta["grip_mult"] == pytest.approx(1.15)
    assert meta["name"] == "Cascavel Modified"

    # The source file must be untouched
    assert _sha256(SOURCE_TRACK) == source_hash_before


def test_reader_tolerates_missing_grip_attr() -> None:
    """Legacy files without grip_mult read back with a 1.0 default."""
    _, meta = CircuitHDF5Reader(str(SOURCE_TRACK)).read_circuit()
    assert meta["grip_mult"] == pytest.approx(1.0)
