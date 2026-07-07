"""
Tests for the parameterized speed governor (speed_limit_kmh).

Copa Truck regulation imposes a 200 km/h governor. Previously hardcoded in
_build_flat_params(); now a VehicleParams field so other categories or
regulation revisions do not require code changes.

Back-compat contract:
- Presets without the field: Truck category keeps the 200 km/h governor.
- Non-truck without the field: unlimited (999 m/s sentinel).
- Explicit value in JSON/params overrides everything.
"""
from __future__ import annotations

import pytest

from src.simulation.lap_time_solver import _build_flat_params
from src.vehicle.parameters import VehicleParams, copa_truck_2dof_default

KMH_TO_MS = 1.0 / 3.6
UNLIMITED_SENTINEL_MS = 999.0


def _truck() -> VehicleParams:
    return copa_truck_2dof_default()


def test_default_truck_keeps_200kmh_governor():
    vp = _truck()
    p = _build_flat_params(vp)
    assert p.speed_limit == pytest.approx(200.0 * KMH_TO_MS)


def test_explicit_speed_limit_overrides_governor():
    vp = _truck()
    vp.speed_limit_kmh = 180.0
    p = _build_flat_params(vp)
    assert p.speed_limit == pytest.approx(180.0 * KMH_TO_MS)


def test_non_truck_without_limit_is_unlimited():
    vp = _truck()
    vp.category = "Formula"
    vp.name = "generic single seater"
    p = _build_flat_params(vp)
    assert p.speed_limit == pytest.approx(UNLIMITED_SENTINEL_MS)


def test_non_truck_with_explicit_limit_respects_it():
    vp = _truck()
    vp.category = "Formula"
    vp.name = "limited prototype"
    vp.speed_limit_kmh = 250.0
    p = _build_flat_params(vp)
    assert p.speed_limit == pytest.approx(250.0 * KMH_TO_MS)


def test_from_dict_roundtrip_preserves_speed_limit():
    vp = _truck()
    vp.speed_limit_kmh = 190.0
    data = vp.to_dict()
    vp2 = VehicleParams.from_dict(data)
    assert vp2.speed_limit_kmh == pytest.approx(190.0)


def test_from_dict_without_field_defaults_to_zero_sentinel():
    vp = _truck()
    data = vp.to_dict()
    data.pop("speed_limit_kmh", None)
    vp2 = VehicleParams.from_dict(data)
    assert vp2.speed_limit_kmh == 0.0
