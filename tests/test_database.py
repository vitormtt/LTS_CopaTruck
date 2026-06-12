"""
Unit and integration tests for PostgreSQL database functionality and its fallback mechanism.
"""

import os
import shutil
import pytest
from pathlib import Path
from src.database import db_manager

# Temporary directory for fallback testing to avoid modifying production data
TEST_DATA_DIR = Path(__file__).resolve().parent / "test_data"

@pytest.fixture(autouse=True)
def setup_test_directories():
    """Create a temporary data directory for database testing fallback."""
    # Override paths in db_manager temporarily for the tests
    old_vehicles_path = db_manager.VEHICLES_JSON_PATH
    old_results_path = db_manager.RESULTS_JSON_PATH
    old_files_path = db_manager.FILES_JSON_PATH
    old_data_dir = db_manager.DATA_DIR
    
    TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
    db_manager.DATA_DIR = TEST_DATA_DIR
    db_manager.VEHICLES_JSON_PATH = TEST_DATA_DIR / "vehicle_models.json"
    db_manager.RESULTS_JSON_PATH = TEST_DATA_DIR / "simulation_results.json"
    db_manager.FILES_JSON_PATH = TEST_DATA_DIR / "files_metadata.json"
    
    yield
    
    # Restore original paths
    db_manager.VEHICLES_JSON_PATH = old_vehicles_path
    db_manager.RESULTS_JSON_PATH = old_results_path
    db_manager.FILES_JSON_PATH = old_files_path
    db_manager.DATA_DIR = old_data_dir
    
    # Clean up test directory
    if TEST_DATA_DIR.exists():
        shutil.rmtree(TEST_DATA_DIR)


def test_db_availability_check() -> None:
    """Verify that is_db_available returns a boolean without throwing exceptions."""
    available = db_manager.is_db_available()
    assert isinstance(available, bool)


def test_vehicle_save_and_retrieve_fallback() -> None:
    """Test saving and retrieving vehicle using local JSON database fallback."""
    # Force DB disabled to test JSON fallback behavior
    old_disabled = db_manager._db_disabled
    db_manager._db_disabled = True
    
    try:
        test_params = {
            "m": 4500.0,
            "lf": 2.15,
            "lr": 2.25,
            "h_cg": 1.1,
            "Cf": 135000.0,
            "Cr": 135000.0,
            "mu": 1.6,
            "r_wheel": 0.65,
            "P_max": 850000.0,
            "T_max": 4200.0,
            "rpm_max": 3500.0,
            "rpm_idle": 800.0,
            "n_gears": 12,
            "gear_ratios": [14.5, 10.8, 8.0, 6.0, 4.5, 3.4, 2.6, 2.0, 1.55, 1.2, 1.0, 0.75],
            "final_drive": 4.0,
            "max_decel": 9.2,
            "Cx": 0.7,
            "A_front": 8.7,
            "Cl": 0.05,
            "max_brake_force": 60000.0,
            "brake_balance": 60.0,
            "Iz": 15000.0,
            "torque_curve_rpm": [800.0, 1750.0, 2800.0, 3325.0, 3500.0],
            "torque_curve_nm": [1680.0, 4200.0, 3990.0, 3360.0, 2520.0],
            "abs_enabled": True
        }
        
        # Save vehicle
        success = db_manager.save_vehicle(
            vehicle_id="test_truck",
            name="Test Copa Truck",
            manufacturer="VW-Test",
            year=2026,
            category="Truck",
            params=test_params
        )
        assert success is True
        
        # Verify fallback JSON was created
        assert db_manager.VEHICLES_JSON_PATH.exists()
        
        # Retrieve vehicle
        retrieved = db_manager.get_vehicle("test_truck")
        assert retrieved is not None
        assert retrieved["name"] == "Test Copa Truck"
        assert retrieved["manufacturer"] == "VW-Test"
        assert retrieved["year"] == 2026
        assert retrieved["category"] == "Truck"
        assert retrieved["m"] == 4500.0
        
        # List vehicles
        vehicle_list = db_manager.list_vehicles()
        assert "test_truck" in vehicle_list
        assert vehicle_list["test_truck"] == "Test Copa Truck"
        
    finally:
        db_manager._db_disabled = old_disabled


def test_simulation_results_save_and_list_fallback() -> None:
    """Test saving and listing simulation results fallback."""
    old_disabled = db_manager._db_disabled
    db_manager._db_disabled = True
    
    try:
        success = db_manager.save_simulation_result(
            vehicle_id="volkswagen_31320",
            track_id="cascavel",
            mode="qualifying",
            setup_name="default",
            lap_time=79.45,
            avg_speed_kmh=145.0,
            max_speed_kmh=194.3,
            peak_lat_g=1.41,
            peak_brake_g=1.1,
            peak_accel_g=0.6,
            time_wot_pct=76.4,
            time_braking_pct=23.3,
            fuel_total_l=2.64,
            final_tyre_temp_c=53.5,
            final_tyre_pressure_bar=2.14,
            csv_path="/tmp/test_sim.csv"
        )
        assert success is True
        
        # Retrieve simulation results
        results = db_manager.list_simulation_results()
        assert len(results) == 1
        assert results[0]["vehicle_id"] == "volkswagen_31320"
        assert results[0]["track_id"] == "cascavel"
        assert results[0]["lap_time"] == 79.45
        
        # Test filtering
        results_filtered = db_manager.list_simulation_results(vehicle_id="scania_r480")
        assert len(results_filtered) == 0
        
    finally:
        db_manager._db_disabled = old_disabled


def test_files_metadata_save_and_list_fallback() -> None:
    """Test saving and listing files metadata fallback."""
    old_disabled = db_manager._db_disabled
    db_manager._db_disabled = True
    
    try:
        success = db_manager.save_file_metadata(
            file_name="telemetry_cascavel.csv",
            file_type="csv",
            file_path="/home/vitor/data/telemetry_cascavel.csv"
        )
        assert success is True
        
        # Retrieve file metadata
        files = db_manager.list_files_metadata()
        assert len(files) == 1
        assert files[0]["file_name"] == "telemetry_cascavel.csv"
        assert files[0]["file_type"] == "csv"
        assert files[0]["file_path"] == "/home/vitor/data/telemetry_cascavel.csv"
        
        # Test filtering
        files_filtered = db_manager.list_files_metadata(file_type="pdf")
        assert len(files_filtered) == 0
        
    finally:
        db_manager._db_disabled = old_disabled
