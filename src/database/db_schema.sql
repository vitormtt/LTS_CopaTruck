-- src/database/db_schema.sql
-- Database schema for LapTimeSimulator_CopaTruck

-- 1. Table: vehicles
CREATE TABLE IF NOT EXISTS vehicles (
    vehicle_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    manufacturer VARCHAR(100),
    year INTEGER,
    category VARCHAR(50) DEFAULT 'Truck',
    params JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast JSONB querying on parameters
CREATE INDEX IF NOT EXISTS idx_vehicles_params ON vehicles USING gin (params);

-- 2. Table: simulation_results
CREATE TABLE IF NOT EXISTS simulation_results (
    id SERIAL PRIMARY KEY,
    vehicle_id VARCHAR(50) NOT NULL REFERENCES vehicles(vehicle_id) ON DELETE CASCADE,
    track_id VARCHAR(50) NOT NULL,
    mode VARCHAR(50) NOT NULL,
    setup_name VARCHAR(100) NOT NULL,
    lap_time DOUBLE PRECISION NOT NULL,
    avg_speed_kmh DOUBLE PRECISION,
    max_speed_kmh DOUBLE PRECISION,
    peak_lat_g DOUBLE PRECISION,
    peak_brake_g DOUBLE PRECISION,
    peak_accel_g DOUBLE PRECISION,
    time_wot_pct DOUBLE PRECISION,
    time_braking_pct DOUBLE PRECISION,
    fuel_total_l DOUBLE PRECISION,
    final_tyre_temp_c DOUBLE PRECISION,
    final_tyre_pressure_bar DOUBLE PRECISION,
    csv_path VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sim_results_vehicle ON simulation_results (vehicle_id);
CREATE INDEX IF NOT EXISTS idx_sim_results_track ON simulation_results (track_id);

-- 3. Table: files_metadata
CREATE TABLE IF NOT EXISTS files_metadata (
    id SERIAL PRIMARY KEY,
    file_name VARCHAR(100) NOT NULL,
    file_type VARCHAR(50) NOT NULL, -- 'pdf', 'csv', 'hdf5', 'xrk'
    file_path VARCHAR(255) UNIQUE NOT NULL,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
