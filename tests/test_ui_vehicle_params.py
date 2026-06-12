"""
Headless UI tests for the vehicle parameters page (streamlit AppTest).

Covers the two behaviours behind the model-management flow:
1. switching the selected model re-seeds every parameter widget (stale
   session-state keys previously leaked the old model's numbers);
2. "Save as New Model" persists a copy through db_manager and the new
   model becomes selected, leaving the base presets untouched.
"""

import json

import pytest
from streamlit.testing.v1 import AppTest

from src.database import db_manager
from src.vehicle import fleet


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    """Redirect db_manager fallback JSON to a temp copy and force JSON mode."""
    src_path = db_manager.VEHICLES_JSON_PATH
    tmp_vehicles = tmp_path / "vehicle_models.json"
    tmp_vehicles.write_text(src_path.read_text(encoding="utf-8"), encoding="utf-8")

    monkeypatch.setattr(db_manager, "_db_disabled", True)
    monkeypatch.setattr(db_manager, "DATA_DIR", tmp_path)
    monkeypatch.setattr(db_manager, "VEHICLES_JSON_PATH", tmp_vehicles)
    monkeypatch.setattr(db_manager, "RESULTS_JSON_PATH", tmp_path / "simulation_results.json")
    monkeypatch.setattr(db_manager, "FILES_JSON_PATH", tmp_path / "files_metadata.json")
    # Point the fleet JSON fallback at the temp copy as well, then reset caches
    monkeypatch.setattr(
        fleet, "_load_json_models", _patched_loader(tmp_vehicles), raising=True
    )
    fleet.refresh_fleet()
    yield
    fleet.refresh_fleet()


def _patched_loader(json_path):
    from src.vehicle.parameters import VehicleParams, validate_vehicle_params

    def _loader():
        if fleet._JSON_MODELS_CACHE:
            return
        # Mirror the production loader: database first, JSON file fallback
        try:
            db_vehicles = db_manager.list_vehicles()
        except Exception:
            db_vehicles = {}
        data = {}
        if db_vehicles:
            for key in db_vehicles:
                val = db_manager.get_vehicle(key)
                if val:
                    data[key] = val
        if not data:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        for key, val in data.items():
            vp = VehicleParams.from_solver_dict(val)
            if "name" in val:
                vp.name = val["name"]
            if not validate_vehicle_params(vp):
                fleet._JSON_MODELS_CACHE[key] = vp

    return _loader


def _page_test() -> AppTest:
    at = AppTest.from_function(_run_page)
    at.run(timeout=30)
    assert not at.exception, at.exception
    return at


def _run_page():
    from src.visualization.components.vehicle_params import parametros_veiculo_page
    parametros_veiculo_page()


def _input_value(at: AppTest, key: str):
    return at.number_input(key=key).value


def test_switching_model_reseeds_widgets():
    at = _page_test()
    # First model in the fleet JSON is the VW 31320 (4500 kg, wb 4.40 m)
    assert at.selectbox[0].value == "volkswagen_31320"
    assert _input_value(at, "vp_mass") == pytest.approx(4500.0)
    assert _input_value(at, "vp_wheelbase") == pytest.approx(4.40)

    at.selectbox[0].select("scania_r480").run(timeout=30)
    assert not at.exception

    # Widgets must show the Scania numbers, not the stale VW ones
    assert _input_value(at, "vp_mass") == pytest.approx(4600.0)
    assert _input_value(at, "vp_wheelbase") == pytest.approx(4.70)


def test_save_as_new_model_persists_copy_and_selects_it():
    at = _page_test()
    assert at.selectbox[0].value == "volkswagen_31320"

    # Make the VW copy regulation-compliant via the page widgets
    at.number_input(key="vp_mass").set_value(4950.0)
    at.number_input(key="vp_wheelbase").set_value(3.60)
    at.slider(key="vp_wd_front").set_value(54.0)  # front axle >= 2520 kg
    at.number_input(key="vp_tw_front").set_value(2.14)
    at.number_input(key="vp_tw_rear").set_value(2.14)
    at.text_input(key="new_model_name").set_value("VW 31320 (UI Test Copy)")
    at.text_input(key="new_model_id").set_value("vw_31320_ui_test_copy")
    at.run(timeout=30)
    assert not at.exception

    at.button(key="btn_save_new_model").click().run(timeout=30)
    assert not at.exception

    # New model persisted in storage…
    stored = json.loads(db_manager.VEHICLES_JSON_PATH.read_text(encoding="utf-8"))
    assert "vw_31320_ui_test_copy" in stored
    assert stored["vw_31320_ui_test_copy"]["m"] == pytest.approx(4950.0)
    # …base preset untouched…
    assert stored["volkswagen_31320"]["m"] == pytest.approx(4500.0)
    # …and now selected in the UI with its own numbers loaded.
    assert at.selectbox[0].value == "vw_31320_ui_test_copy"
    assert _input_value(at, "vp_mass") == pytest.approx(4950.0)


def test_save_as_new_model_rejects_duplicate_id():
    at = _page_test()
    at.number_input(key="vp_mass").set_value(4950.0)
    at.number_input(key="vp_wheelbase").set_value(3.60)
    at.slider(key="vp_wd_front").set_value(54.0)
    at.number_input(key="vp_tw_front").set_value(2.14)
    at.number_input(key="vp_tw_rear").set_value(2.14)
    at.text_input(key="new_model_id").set_value("scania_r480")  # already exists
    at.run(timeout=30)

    at.button(key="btn_save_new_model").click().run(timeout=30)
    assert not at.exception
    assert any("already exists" in str(e.value) for e in at.error)
