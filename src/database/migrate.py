"""
Idempotent database migration: JSONB vehicle params -> relational tables.

Steps:
1. Apply db_schema.sql (CREATE TABLE IF NOT EXISTS — safe on any state).
2. If vehicles.params (legacy JSONB column) exists, decompose every row
   into the subsystem tables through db_manager.save_vehicle and drop
   the column afterwards.

Run inside the app container:  python src/database/migrate.py
(or `make migrate` from the host).
"""

import sys
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.database import db_manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("migrate")

SCHEMA_PATH = Path(__file__).resolve().parent / "db_schema.sql"


def migrate() -> bool:
    if not db_manager.is_db_available():
        logger.error("PostgreSQL is not reachable — start the db service first (make up).")
        return False

    conn = db_manager.get_connection()
    try:
        with conn.cursor() as cursor:
            logger.info("Applying relational schema (CREATE TABLE IF NOT EXISTS)...")
            cursor.execute(SCHEMA_PATH.read_text(encoding="utf-8"))

            cursor.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'vehicles' AND column_name = 'params'
                """
            )
            has_legacy_column = cursor.fetchone() is not None
        conn.commit()

        if not has_legacy_column:
            logger.info("No legacy vehicles.params column — schema is already relational.")
            return True

        # The legacy column was NOT NULL; relax it so the new save path
        # (which no longer writes params) can upsert during migration.
        with conn.cursor() as cursor:
            cursor.execute("ALTER TABLE vehicles ALTER COLUMN params DROP NOT NULL")
        conn.commit()

        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT vehicle_id, name, manufacturer, year, category, params FROM vehicles"
            )
            rows = cursor.fetchall()
        logger.info("Migrating %d vehicle(s) from JSONB to relational tables...", len(rows))

        migrated = 0
        for vehicle_id, name, manufacturer, year, category, params in rows:
            if not isinstance(params, dict):
                logger.warning("Vehicle '%s' has no parseable params — skipped.", vehicle_id)
                continue
            db_manager.save_vehicle(
                vehicle_id=vehicle_id,
                name=name,
                manufacturer=manufacturer or "",
                year=year or 0,
                category=category or "Truck",
                params=params,
            )
            # save_vehicle returns True even on JSON fallback — verify the
            # rows actually landed in the database before counting.
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM vehicle_mass_geometry WHERE vehicle_id = %s",
                    (vehicle_id,),
                )
                if cursor.fetchone():
                    migrated += 1
                else:
                    logger.error("Vehicle '%s' did not reach the database.", vehicle_id)

        if migrated == len(rows):
            with conn.cursor() as cursor:
                logger.info("Dropping legacy vehicles.params column...")
                cursor.execute("ALTER TABLE vehicles DROP COLUMN params")
            conn.commit()
            logger.info("Migration complete: %d/%d vehicles relational.", migrated, len(rows))
            return True

        logger.error(
            "Migrated %d/%d — legacy column kept for retry. Fix the errors and rerun.",
            migrated, len(rows),
        )
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(0 if migrate() else 1)
