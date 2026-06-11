"""
Tests for advanced vehicle input plumbing: transmission validation
and unit conversion helpers.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.vehicle.parameters import TransmissionParams  # noqa: E402
from src.vehicle.units import PSI_PER_BAR, bar_to_psi, psi_to_bar  # noqa: E402


def test_transmission_gear_count_mismatch_raises() -> None:
    """gear_ratios length must match num_gears."""
    with pytest.raises(ValueError, match="gear_ratios length"):
        TransmissionParams(
            num_gears=6,
            gear_ratios=[14.0, 10.5, 7.8],
            final_drive_ratio=4.0,
        )


def test_transmission_consistent_passes() -> None:
    tp = TransmissionParams(
        num_gears=3,
        gear_ratios=[14.0, 10.5, 7.8],
        final_drive_ratio=4.0,
    )
    assert tp.num_gears == len(tp.gear_ratios)


def test_psi_bar_round_trip() -> None:
    """29 psi ≈ 2.0 bar and conversions invert within 1e-3."""
    assert psi_to_bar(29.0) == pytest.approx(2.0, abs=1e-3)
    assert bar_to_psi(psi_to_bar(26.0)) == pytest.approx(26.0, abs=1e-9)
    assert psi_to_bar(PSI_PER_BAR) == pytest.approx(1.0, abs=1e-12)
