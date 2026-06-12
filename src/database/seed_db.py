"""
Database seeding script.

Loads the fleet presets from data/vehicle_models.json and populates
the PostgreSQL database.
"""

import sys
import json
import logging
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.database import db_manager

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("seed_db")

def seed_database():
    """Migrate JSON fleet presets to PostgreSQL."""
    json_path = ROOT / "data" / "vehicle_models.json"
    if not json_path.exists():
        logger.error(f"Presets file not found at: {json_path}")
        return False
        
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            presets = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read presets from {json_path}: {e}")
        return False
        
    # Check connection
    if not db_manager.is_db_available():
        logger.error("PostgreSQL database is not available for seeding. Please start the docker container.")
        return False
        
    logger.info(f"Found {len(presets)} presets. Seeding database...")
    
    success_count = 0
    for vehicle_id, data in presets.items():
        name = data.get("name", vehicle_id)
        manufacturer = data.get("manufacturer", "Unknown")
        year = data.get("year", 2024)
        category = data.get("category", "Truck")
        
        # Strip metadata from the parameters dictionary to keep clean parameters
        params_dict = dict(data)
        
        # Save to database
        success = db_manager.save_vehicle(
            vehicle_id=vehicle_id,
            name=name,
            manufacturer=manufacturer,
            year=year,
            category=category,
            params=params_dict
        )
        
        if success:
            logger.info(f"Successfully seeded vehicle: {vehicle_id}")
            success_count += 1
        else:
            logger.error(f"Failed to seed vehicle: {vehicle_id}")
            
    logger.info(f"Seeding completed. {success_count}/{len(presets)} vehicles seeded.")
    return success_count == len(presets)

if __name__ == "__main__":
    seed_database()
