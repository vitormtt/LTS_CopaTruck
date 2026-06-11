"""
Guard test: no residual Porsche/GT3 references in active source code.

The Porsche GT3 Cup vehicle was archived to ``_archive/porsche_backup/``.
This test ensures no active code under ``src/`` reintroduces references,
except for two whitelisted historical literature citations (telemetry
channel nomenclature sourced from Pi Toolbox / Porsche Carrera Cup Brasil).
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

# Files allowed to cite Porsche Carrera Cup as a historical data reference
# (telemetry naming conventions only — no code paths).
WHITELIST = {
    SRC / "simulation" / "lap_time_solver.py",
    SRC / "simulation" / "simulation_modes.py",
}

PATTERN = re.compile(r"porsche|gt3", re.IGNORECASE)


def test_no_porsche_references_in_active_code() -> None:
    """Active source files must not reference Porsche/GT3."""
    offenders = []
    for path in sorted(SRC.rglob("*.py")):
        if path in WHITELIST or "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if PATTERN.search(line):
                offenders.append(f"{path.relative_to(ROOT)}:{lineno}: {line.strip()}")
    assert not offenders, (
        "Residual Porsche/GT3 references found in active code:\n"
        + "\n".join(offenders)
    )


def test_porsche_factory_removed() -> None:
    """The archived Porsche factory must not be importable."""
    with pytest.raises(ImportError):
        from src.vehicle.parameters import porsche_911_gt3_cup_991  # noqa: F401
