-- src/database/db_schema.sql
-- Relational schema for LapTimeSimulator_CopaTruck.
--
-- Design: one table per vehicle subsystem, mirroring the VehicleParams
-- dataclass composition (the SSoT in src/vehicle/parameters.py):
--   vehicles 1:1 mass_geometry / tires / engine / transmission /
--                 brakes / aero / fuel
--   vehicles 1:N gear_ratios (ordered) and torque_curve (rpm-indexed)
-- Editing a single parameter touches a single typed column instead of
-- rewriting an opaque JSON blob.

-- 1. Vehicle identity
CREATE TABLE IF NOT EXISTS vehicles (
    vehicle_id   VARCHAR(50) PRIMARY KEY,
    name         VARCHAR(100) NOT NULL,
    manufacturer VARCHAR(100),
    year         INTEGER,
    category     VARCHAR(50) DEFAULT 'Truck',
    created_at   TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Mass & geometry (VehicleMassGeometry + roll stiffness)
CREATE TABLE IF NOT EXISTS vehicle_mass_geometry (
    vehicle_id        VARCHAR(50) PRIMARY KEY REFERENCES vehicles(vehicle_id) ON DELETE CASCADE,
    mass_kg           DOUBLE PRECISION NOT NULL,
    lf_m              DOUBLE PRECISION NOT NULL,
    lr_m              DOUBLE PRECISION NOT NULL,
    cg_height_m       DOUBLE PRECISION NOT NULL,
    track_width_front_m DOUBLE PRECISION,
    track_width_rear_m  DOUBLE PRECISION,
    iz_kgm2           DOUBLE PRECISION,
    k_roll_front      DOUBLE PRECISION,
    k_roll_rear       DOUBLE PRECISION
);

-- 3. Tires (TireParams)
CREATE TABLE IF NOT EXISTS vehicle_tires (
    vehicle_id      VARCHAR(50) PRIMARY KEY REFERENCES vehicles(vehicle_id) ON DELETE CASCADE,
    cf_n_per_rad    DOUBLE PRECISION,
    cr_n_per_rad    DOUBLE PRECISION,
    mu              DOUBLE PRECISION NOT NULL,
    wheel_radius_m  DOUBLE PRECISION NOT NULL,
    pacejka_b       DOUBLE PRECISION,
    pacejka_c       DOUBLE PRECISION,
    pacejka_d       DOUBLE PRECISION,
    pacejka_e       DOUBLE PRECISION,
    p_cold_bar      DOUBLE PRECISION,
    p_cold_lf_psi   DOUBLE PRECISION,
    p_cold_fr_psi   DOUBLE PRECISION,
    p_cold_lr_psi   DOUBLE PRECISION,
    p_cold_rr_psi   DOUBLE PRECISION
);

-- 4. Engine (EngineParams; torque curve normalized in its own table)
CREATE TABLE IF NOT EXISTS vehicle_engine (
    vehicle_id     VARCHAR(50) PRIMARY KEY REFERENCES vehicles(vehicle_id) ON DELETE CASCADE,
    max_power_w    DOUBLE PRECISION NOT NULL,
    max_torque_nm  DOUBLE PRECISION NOT NULL,
    rpm_max        DOUBLE PRECISION NOT NULL,
    rpm_idle       DOUBLE PRECISION NOT NULL,
    bsfc_g_per_kwh DOUBLE PRECISION
);

-- 5. Transmission (TransmissionParams; ratios normalized below)
CREATE TABLE IF NOT EXISTS vehicle_transmission (
    vehicle_id            VARCHAR(50) PRIMARY KEY REFERENCES vehicles(vehicle_id) ON DELETE CASCADE,
    final_drive           DOUBLE PRECISION NOT NULL,
    shift_time_s          DOUBLE PRECISION,
    driveline_efficiency  DOUBLE PRECISION,
    upshift_rpm           DOUBLE PRECISION,
    downshift_rpm         DOUBLE PRECISION
);

-- 6. Brakes (BrakeParams incl. thermal/fade model)
CREATE TABLE IF NOT EXISTS vehicle_brakes (
    vehicle_id              VARCHAR(50) PRIMARY KEY REFERENCES vehicles(vehicle_id) ON DELETE CASCADE,
    max_brake_force_n       DOUBLE PRECISION,
    brake_balance_pct       DOUBLE PRECISION,
    max_decel_ms2           DOUBLE PRECISION,
    abs_enabled             BOOLEAN,
    abs_slip_target         DOUBLE PRECISION,
    brake_response_time_s   DOUBLE PRECISION,
    disc_thermal_efficiency DOUBLE PRECISION,
    disc_mass_kg            DOUBLE PRECISION,
    disc_specific_heat      DOUBLE PRECISION,
    disc_convection         DOUBLE PRECISION,
    disc_area_m2            DOUBLE PRECISION,
    disc_initial_temp_c     DOUBLE PRECISION,
    fade_onset_temp_c       DOUBLE PRECISION,
    fade_full_temp_c        DOUBLE PRECISION,
    fade_min_factor         DOUBLE PRECISION
);

-- 7. Aerodynamics (AeroParams)
CREATE TABLE IF NOT EXISTS vehicle_aero (
    vehicle_id      VARCHAR(50) PRIMARY KEY REFERENCES vehicles(vehicle_id) ON DELETE CASCADE,
    cx              DOUBLE PRECISION NOT NULL,
    frontal_area_m2 DOUBLE PRECISION NOT NULL,
    cl              DOUBLE PRECISION
);

-- 8. Fuel model (VehicleParams root-level fields)
CREATE TABLE IF NOT EXISTS vehicle_fuel (
    vehicle_id            VARCHAR(50) PRIMARY KEY REFERENCES vehicles(vehicle_id) ON DELETE CASCADE,
    initial_fuel_l        DOUBLE PRECISION,
    fuel_density_kg_per_l DOUBLE PRECISION,
    fuel_per_km_l         DOUBLE PRECISION
);

-- 9. Gear ratios — ordered 1:N
CREATE TABLE IF NOT EXISTS vehicle_gear_ratios (
    vehicle_id  VARCHAR(50) REFERENCES vehicles(vehicle_id) ON DELETE CASCADE,
    gear_number SMALLINT NOT NULL CHECK (gear_number >= 1),
    ratio       DOUBLE PRECISION NOT NULL CHECK (ratio > 0),
    PRIMARY KEY (vehicle_id, gear_number)
);

-- 10. Engine torque curve — rpm-indexed 1:N
CREATE TABLE IF NOT EXISTS vehicle_torque_curve (
    vehicle_id VARCHAR(50) REFERENCES vehicles(vehicle_id) ON DELETE CASCADE,
    rpm        DOUBLE PRECISION NOT NULL CHECK (rpm >= 0),
    torque_nm  DOUBLE PRECISION NOT NULL CHECK (torque_nm >= 0),
    PRIMARY KEY (vehicle_id, rpm)
);

-- 11. Simulation results (unchanged — already relational)
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

-- 12. File metadata (unchanged)
CREATE TABLE IF NOT EXISTS files_metadata (
    id SERIAL PRIMARY KEY,
    file_name VARCHAR(100) NOT NULL,
    file_type VARCHAR(50) NOT NULL, -- 'pdf', 'csv', 'hdf5', 'xrk'
    file_path VARCHAR(255) UNIQUE NOT NULL,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
