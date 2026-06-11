"""
Import hygiene test: every module under ``src/`` must import cleanly.

Walks the ``src`` package with pkgutil and imports each module via
importlib. This catches archiving regressions (a live module importing
something that was moved to ``_archive/``) and any other import-time
breakage (syntax errors, module-level side effects raising, renamed
symbols in ``__init__`` re-exports).

Modules whose import fails ONLY because an optional third-party
dependency is not installed in the test environment (e.g. ``libxrk``
for AiM .xrk telemetry parsing) are skipped, not failed — but a missing
*internal* module (anything under ``src.``) always fails.

Author: Lap Time Simulator Team
Date: 2026-06-11
"""
import importlib
import pkgutil
import sys
from pathlib import Path
from typing import Iterator, List

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import src  # noqa: E402


def _walk_src_module_names() -> List[str]:
    """Collect the fully qualified name of every module under src/."""

    def _iter() -> Iterator[str]:
        for info in pkgutil.walk_packages(src.__path__, prefix="src."):
            yield info.name

    return sorted(_iter())


ALL_SRC_MODULES = _walk_src_module_names()

# Modules archived to _archive/dead_modules/ — must NOT be importable
# from the live package anymore.
ARCHIVED_MODULES = [
    "src.optimization",
    "src.simulation.driver_model",
    "src.simulation.validation",
    "src.vehicle.aerodynamics",
    "src.vehicle.brakes",
    "src.vehicle.tires",
    "src.vehicle.truck_models",
    "src.vehicle.vehicle_model",
    "src.visualization.kpi_dashboard",
    "src.visualization.track_plotter",
]


def test_module_discovery_is_sane() -> None:
    """The walker must find the core packages (guard against silent no-op)."""
    assert "src.simulation.lap_time_solver" in ALL_SRC_MODULES
    assert "src.vehicle.parameters" in ALL_SRC_MODULES
    assert "src.visualization.interface" in ALL_SRC_MODULES
    assert len(ALL_SRC_MODULES) >= 20


@pytest.mark.parametrize("module_name", ALL_SRC_MODULES)
def test_module_imports_cleanly(module_name: str) -> None:
    """Every live module under src/ imports without errors."""
    try:
        importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        missing_root = (exc.name or "").split(".")[0]
        if missing_root == "src":
            pytest.fail(
                f"{module_name}: broken internal import "
                f"(archived/renamed module?): {exc}"
            )
        pytest.skip(
            f"{module_name}: optional third-party dependency "
            f"'{exc.name}' not installed"
        )


@pytest.mark.parametrize("module_name", ARCHIVED_MODULES)
def test_archived_modules_are_gone(module_name: str) -> None:
    """Modules moved to _archive/dead_modules/ must not be importable."""
    assert module_name not in ALL_SRC_MODULES
    with pytest.raises(ImportError):
        importlib.import_module(module_name)
