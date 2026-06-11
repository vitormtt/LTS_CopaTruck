"""
Database manager for LapTimeSimulator_CopaTruck.

Manages PostgreSQL connection and execution with a transparent fallback
to local JSON files if database connection fails or dependencies are missing.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger("src.database.db_manager")

# Configuration from environment variables
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "postgres")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "postgres")

# Fallback JSON paths
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
VEHICLES_JSON_PATH = DATA_DIR / "vehicle_models.json"
RESULTS_JSON_PATH = DATA_DIR / "simulation_results.json"
FILES_JSON_PATH = DATA_DIR / "files_metadata.json"

# Global state to track database availability
_db_disabled = False

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    logger.warning("psycopg2 is not installed. Database functionality will fallback to JSON files.")
    _db_disabled = True


def get_connection():
    """Establish and return a connection to the PostgreSQL database."""
    if _db_disabled:
        raise psycopg2.InterfaceError("Database connection is disabled due to missing psycopg2 package.")
    
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        connect_timeout=3
    )


def is_db_available() -> bool:
    """Check if the database is accessible."""
    if _db_disabled:
        return False
    try:
        conn = get_connection()
        conn.close()
        return True
    except Exception as e:
        logger.warning(f"Database not available, falling back to JSON storage. Error: {e}")
        return False


# --- VEHICLES MANAGEMENT ---

def save_vehicle(vehicle_id: str, name: str, manufacturer: str, year: int, category: str, params: Dict[str, Any]) -> bool:
    """Save or update a vehicle's specifications."""
    # Ensure local directory exists for fallback
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Try database first
    if not _db_disabled:
        try:
            conn = get_connection()
            with conn.cursor() as cursor:
                # Upsert into vehicles
                query = """
                INSERT INTO vehicles (vehicle_id, name, manufacturer, year, category, params, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (vehicle_id) DO UPDATE
                SET name = EXCLUDED.name,
                    manufacturer = EXCLUDED.manufacturer,
                    year = EXCLUDED.year,
                    category = EXCLUDED.category,
                    params = EXCLUDED.params,
                    updated_at = CURRENT_TIMESTAMP;
                """
                cursor.execute(query, (vehicle_id, name, manufacturer, year, category, json.dumps(params)))
            conn.commit()
            conn.close()
            logger.info(f"Vehicle '{vehicle_id}' saved to database successfully.")
            
            # Also keep local JSON updated to keep them in sync
            _save_vehicle_locally(vehicle_id, name, manufacturer, year, category, params)
            return True
        except Exception as e:
            logger.warning(f"Failed to save vehicle '{vehicle_id}' to database. Falling back to local storage. Error: {e}")

    # Fallback to local JSON
    return _save_vehicle_locally(vehicle_id, name, manufacturer, year, category, params)


def _save_vehicle_locally(vehicle_id: str, name: str, manufacturer: str, year: int, category: str, params: Dict[str, Any]) -> bool:
    """Helper to save vehicle to local json file."""
    try:
        data = {}
        if VEHICLES_JSON_PATH.exists():
            with open(VEHICLES_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        
        # Merge basic parameters and custom params dict
        vehicle_entry = dict(params)
        vehicle_entry["name"] = name
        vehicle_entry["manufacturer"] = manufacturer
        vehicle_entry["year"] = year
        vehicle_entry["category"] = category
        
        data[vehicle_id] = vehicle_entry
        
        with open(VEHICLES_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Failed to save vehicle '{vehicle_id}' locally: {e}")
        return False


def get_vehicle(vehicle_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve vehicle specifications by ID."""
    if not _db_disabled:
        try:
            conn = get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT name, manufacturer, year, category, params FROM vehicles WHERE vehicle_id = %s", (vehicle_id,))
                row = cursor.fetchone()
                if row:
                    vehicle_data = dict(row["params"])
                    vehicle_data["name"] = row["name"]
                    vehicle_data["manufacturer"] = row["manufacturer"]
                    vehicle_data["year"] = row["year"]
                    vehicle_data["category"] = row["category"]
                    conn.close()
                    return vehicle_data
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to get vehicle '{vehicle_id}' from database. Falling back to local storage. Error: {e}")

    # Fallback
    if VEHICLES_JSON_PATH.exists():
        try:
            with open(VEHICLES_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get(vehicle_id)
        except Exception as e:
            logger.error(f"Error reading local vehicles database: {e}")
    return None


def list_vehicles() -> Dict[str, str]:
    """List all vehicles mapping vehicle_id -> display name."""
    if not _db_disabled:
        try:
            conn = get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT vehicle_id, name FROM vehicles")
                rows = cursor.fetchall()
                conn.close()
                return {row["vehicle_id"]: row["name"] for row in rows}
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to list vehicles from database. Falling back to local storage. Error: {e}")

    # Fallback
    if VEHICLES_JSON_PATH.exists():
        try:
            with open(VEHICLES_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {vid: val.get("name", vid) for vid, val in data.items()}
        except Exception as e:
            logger.error(f"Error reading local vehicles database: {e}")
    return {}


# --- SIMULATION RESULTS MANAGEMENT ---

def save_simulation_result(
    vehicle_id: str,
    track_id: str,
    mode: str,
    setup_name: str,
    lap_time: float,
    avg_speed_kmh: float,
    max_speed_kmh: float,
    peak_lat_g: float,
    peak_brake_g: float,
    peak_accel_g: float,
    time_wot_pct: float,
    time_braking_pct: float,
    fuel_total_l: float,
    final_tyre_temp_c: float,
    final_tyre_pressure_bar: float,
    csv_path: Optional[str] = None
) -> bool:
    """Save simulation summary results."""
    # Ensure local directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    if not _db_disabled:
        try:
            conn = get_connection()
            with conn.cursor() as cursor:
                query = """
                INSERT INTO simulation_results (
                    vehicle_id, track_id, mode, setup_name, lap_time, avg_speed_kmh, max_speed_kmh,
                    peak_lat_g, peak_brake_g, peak_accel_g, time_wot_pct, time_braking_pct,
                    fuel_total_l, final_tyre_temp_c, final_tyre_pressure_bar, csv_path
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """
                cursor.execute(query, (
                    vehicle_id, track_id, mode, setup_name, lap_time, avg_speed_kmh, max_speed_kmh,
                    peak_lat_g, peak_brake_g, peak_accel_g, time_wot_pct, time_braking_pct,
                    fuel_total_l, final_tyre_temp_c, final_tyre_pressure_bar, csv_path
                ))
            conn.commit()
            conn.close()
            logger.info("Simulation result saved to database successfully.")
            return True
        except Exception as e:
            logger.warning(f"Failed to save simulation result to database. Falling back to local storage. Error: {e}")

    # Fallback to local JSON
    try:
        results = []
        if RESULTS_JSON_PATH.exists():
            with open(RESULTS_JSON_PATH, "r", encoding="utf-8") as f:
                results = json.load(f)
                if not isinstance(results, list):
                    results = []
        
        result_entry = {
            "vehicle_id": vehicle_id,
            "track_id": track_id,
            "mode": mode,
            "setup_name": setup_name,
            "lap_time": lap_time,
            "avg_speed_kmh": avg_speed_kmh,
            "max_speed_kmh": max_speed_kmh,
            "peak_lat_g": peak_lat_g,
            "peak_brake_g": peak_brake_g,
            "peak_accel_g": peak_accel_g,
            "time_wot_pct": time_wot_pct,
            "time_braking_pct": time_braking_pct,
            "fuel_total_l": fuel_total_l,
            "final_tyre_temp_c": final_tyre_temp_c,
            "final_tyre_pressure_bar": final_tyre_pressure_bar,
            "csv_path": csv_path,
            "created_at": str(Path().stat().st_mtime) if csv_path and Path(csv_path).exists() else ""
        }
        results.append(result_entry)
        
        with open(RESULTS_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save simulation result locally: {e}")
        return False


def list_simulation_results(vehicle_id: Optional[str] = None, track_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """List simulation results, optionally filtered by vehicle and/or track."""
    if not _db_disabled:
        try:
            conn = get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                query = "SELECT * FROM simulation_results WHERE 1=1"
                params = []
                if vehicle_id:
                    query += " AND vehicle_id = %s"
                    params.append(vehicle_id)
                if track_id:
                    query += " AND track_id = %s"
                    params.append(track_id)
                query += " ORDER BY created_at DESC"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                conn.close()
                return [dict(row) for row in rows]
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to list simulation results from database. Falling back to local storage. Error: {e}")

    # Fallback
    if RESULTS_JSON_PATH.exists():
        try:
            with open(RESULTS_JSON_PATH, "r", encoding="utf-8") as f:
                results = json.load(f)
                if not isinstance(results, list):
                    return []
            
            # Apply filters
            filtered = results
            if vehicle_id:
                filtered = [r for r in filtered if r.get("vehicle_id") == vehicle_id]
            if track_id:
                filtered = [r for r in filtered if r.get("track_id") == track_id]
            
            # Sort by created_at desc if present
            return filtered[::-1]
        except Exception as e:
            logger.error(f"Error reading local simulation results database: {e}")
    return []


# --- FILE METADATA MANAGEMENT ---

def save_file_metadata(file_name: str, file_type: str, file_path: str) -> bool:
    """Register file metadata (PDF, CSV, HDF5, etc.)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    if not _db_disabled:
        try:
            conn = get_connection()
            with conn.cursor() as cursor:
                query = """
                INSERT INTO files_metadata (file_name, file_type, file_path)
                VALUES (%s, %s, %s)
                ON CONFLICT (file_path) DO UPDATE
                SET file_name = EXCLUDED.file_name,
                    file_type = EXCLUDED.file_type;
                """
                cursor.execute(query, (file_name, file_type, file_path))
            conn.commit()
            conn.close()
            logger.info(f"File metadata for '{file_name}' saved to database.")
            return True
        except Exception as e:
            logger.warning(f"Failed to save file metadata to database. Falling back to local storage. Error: {e}")

    # Fallback to local JSON
    try:
        files = {}
        if FILES_JSON_PATH.exists():
            with open(FILES_JSON_PATH, "r", encoding="utf-8") as f:
                files = json.load(f)
        
        files[file_path] = {
            "file_name": file_name,
            "file_type": file_type,
            "file_path": file_path
        }
        
        with open(FILES_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(files, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save file metadata locally: {e}")
        return False


def list_files_metadata(file_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """List metadata for files, optionally filtered by file_type."""
    if not _db_disabled:
        try:
            conn = get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                query = "SELECT * FROM files_metadata WHERE 1=1"
                params = []
                if file_type:
                    query += " AND file_type = %s"
                    params.append(file_type)
                query += " ORDER BY uploaded_at DESC"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                conn.close()
                return [dict(row) for row in rows]
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to list file metadata from database. Falling back to local storage. Error: {e}")

    # Fallback
    if FILES_JSON_PATH.exists():
        try:
            with open(FILES_JSON_PATH, "r", encoding="utf-8") as f:
                files = json.load(f)
            
            flat_list = list(files.values())
            if file_type:
                flat_list = [f for f in flat_list if f.get("file_type") == file_type]
            return flat_list
        except Exception as e:
            logger.error(f"Error reading local files metadata database: {e}")
    return []
