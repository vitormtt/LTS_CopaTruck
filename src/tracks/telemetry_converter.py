"""
Telemetry Converter for AiM .xrk files to standard .csv telemetry.

Author: Lap Time Simulator Team
Date: 2026-06-10
"""
import os
import sys
import numpy as np
import pandas as pd
import pyarrow as pa
from typing import Dict, Any, Optional

from libxrk import aim_xrk
from libxrk.base import LogFile
from libxrk.gps import GPS_CHANNEL_NAMES


def align_gps_timebase(log: LogFile) -> LogFile:
    """
    Detects and corrects clock synchronization offset between GPS and ECU time bases.
    Subtracts the end offset from all GPS timecodes to align with internal logger clock.
    """
    gps_channel_name = None
    for name in GPS_CHANNEL_NAMES:
        if name in log.channels:
            gps_channel_name = name
            break
            
    if gps_channel_name is None:
        return log
        
    gps_time = log.channels[gps_channel_name].column("timecodes").to_numpy()
    if len(gps_time) < 2:
        return log
        
    # Find maximum end time of non-GPS channels
    non_gps_end_times = []
    for ch_name, ch_table in log.channels.items():
        if ch_name not in GPS_CHANNEL_NAMES:
            ch_time = ch_table.column("timecodes").to_numpy()
            if len(ch_time) > 0:
                non_gps_end_times.append(ch_time[-1])
                
    if not non_gps_end_times:
        return log
        
    max_non_gps_end = max(non_gps_end_times)
    gps_end = gps_time[-1]
    offset = gps_end - max_non_gps_end
    
    # If the offset is significant (e.g. > 1 second), apply correction
    if abs(offset) > 1000:
        aligned_channels = {}
        for name, table in log.channels.items():
            if name in GPS_CHANNEL_NAMES:
                t = table.column("timecodes").to_numpy() - offset
                aligned_channels[name] = pa.table({
                    "timecodes": pa.array(t, type=pa.int64()),
                    name: table.column(name)
                })
            else:
                aligned_channels[name] = table
        return LogFile(aligned_channels, log.laps, log.metadata, log.file_name)
        
    return log


def get_fastest_lap_index(laps_table: pa.Table) -> int:
    """Finds the index of the fastest valid lap in the laps table."""
    df_laps = laps_table.to_pandas()
    df_laps["duration_s"] = (df_laps["end_time"] - df_laps["start_time"]) / 1000.0
    
    # Filter for valid complete laps (e.g., > 40s to exclude in/out or aborted laps)
    valid_laps = df_laps[df_laps["duration_s"] > 40.0]
    if valid_laps.empty:
        # Fallback to absolute fastest lap
        return int(df_laps["duration_s"].idxmin())
        
    return int(valid_laps["duration_s"].idxmin())


def convert_xrk_to_csv(xrk_path: str, csv_path: str, lap_num: Optional[int] = None) -> Dict[str, Any]:
    """
    Parses an AiM .xrk file, aligns the timing, extracts the specified (or fastest) lap,
    integrates velocity to compute distance, and saves to a standardized .csv telemetry file.
    
    Returns:
        dict: Session metadata and conversion summary.
    """
    if not os.path.exists(xrk_path):
        raise FileNotFoundError(f"File not found: {xrk_path}")
        
    # Load and align
    raw_log = aim_xrk(xrk_path)
    log = align_gps_timebase(raw_log)
    
    # Determine lap to convert
    laps_list = log.laps.column("num").to_pylist()
    if lap_num is None:
        lap_idx = get_fastest_lap_index(log.laps)
        selected_lap_num = laps_list[lap_idx]
    else:
        if lap_num not in laps_list:
            raise ValueError(f"Requested lap {lap_num} not found. Available: {laps_list}")
        selected_lap_num = lap_num
        
    # Extract lap data
    lap_log = log.filter_by_lap(selected_lap_num)
    df = lap_log.get_channels_as_table().to_pandas()
    
    # Sort and compute timecode offsets
    df = df.sort_values("timecodes").reset_index(drop=True)
    start_time_ms = df["timecodes"].iloc[0]
    df["time"] = (df["timecodes"] - start_time_ms) / 1000.0
    
    # Channel mappings (real name -> standard name)
    mapping = {
        "GPS Speed": "v_kmh",
        "RPM": "rpm",
        "Acelerador": "throttle_pct",
        "GPS_InlineAcc": "ax_long_g",
        "GPS_LateralAcc": "ay_lat_g",
        "GPS Latitude": "lat",
        "GPS Longitude": "lon"
    }
    
    # Ensure columns exist and rename
    out_df = pd.DataFrame()
    out_df["time"] = df["time"]
    
    # GPS Speed is in m/s, convert to km/h and also keep m/s for distance integration
    if "GPS Speed" in df.columns:
        gps_speed_ms = df["GPS Speed"].fillna(0.0).to_numpy()
        out_df["v_kmh"] = gps_speed_ms * 3.6
        
        # Integrate distance
        dt = np.diff(df["time"].to_numpy(), prepend=0.0)
        out_df["distance"] = np.cumsum(gps_speed_ms * dt)
    else:
        out_df["v_kmh"] = 0.0
        out_df["distance"] = 0.0
        gps_speed_ms = np.zeros(len(df))
        
    # Map remaining channels
    for aim_name, std_name in mapping.items():
        if aim_name == "GPS Speed":
            continue
        if aim_name in df.columns:
            out_df[std_name] = df[aim_name]
        else:
            # Fallbacks
            if std_name == "rpm":
                out_df["rpm"] = 0.0
            elif std_name == "throttle_pct":
                out_df["throttle_pct"] = 0.0
            elif std_name in ["ax_long_g", "ay_lat_g"]:
                out_df[std_name] = 0.0
                
    # Estimate Brake percentage if missing (standard in .xrk logs)
    brake_channels = ["Brake", "Freio", "BrakePressure", "Pressao_Freio"]
    found_brake = False
    for b_ch in brake_channels:
        if b_ch in df.columns:
            out_df["brake_pct"] = df[b_ch]
            found_brake = True
            break
            
    if not found_brake:
        # Estimate from longitudinal deceleration (ax_long_g < -0.05)
        # assuming ~0.8g is maximum deceleration (100% brake effort)
        ax = out_df["ax_long_g"].fillna(0.0).to_numpy()
        out_df["brake_pct"] = np.where(ax < -0.05, np.clip(-ax / 0.8 * 100.0, 0.0, 100.0), 0.0)
        
    # Estimate steering wheel angle if not logged
    if "Steering" in df.columns:
        out_df["steering_deg"] = df["Steering"]
    else:
        # Ackermann estimate based on lateral acceleration or curvature:
        # steering_angle = wheelbase / radius * steering_ratio
        # lateral_accel = v^2 / radius  =>  wheelbase * (ay_lat_g * g) / v^2 * ratio
        # Let's keep it simple: scale lateral G-force (1g ~ 90 deg steering wheel deflection)
        ay = out_df["ay_lat_g"].fillna(0.0).to_numpy()
        out_df["steering_deg"] = ay * 90.0
        
    # Add placeholders for tyre temperature and pressure
    out_df["temp_pneu"] = 50.0
    out_df["pressao_pneu"] = 1.8
    out_df["consumo"] = 0.0
    out_df["gear"] = 6  # average mid gear placeholder
    
    # Reorder columns to match simulation result format
    cols_order = [
        "distance", "time", "v_kmh", "ax_long_g", "ay_lat_g",
        "gear", "rpm", "temp_pneu", "consumo", "pressao_pneu",
        "throttle_pct", "brake_pct", "steering_deg"
    ]
    
    # Add missing ones
    for col in cols_order:
        if col not in out_df.columns:
            out_df[col] = 0.0
            
    out_df = out_df[cols_order]
    
    # Save to CSV
    os.makedirs(os.path.dirname(os.path.abspath(csv_path)), exist_ok=True)
    out_df.to_csv(csv_path, index=False)
    
    # Compile metadata
    meta = log.metadata
    lap_time = float(df["time"].iloc[-1])
    
    return {
        "driver": meta.get("Driver", "Unknown"),
        "vehicle": meta.get("Vehicle", "Unknown"),
        "venue": meta.get("Venue", "Unknown"),
        "date": meta.get("Log Date", "Unknown"),
        "lap_number": selected_lap_num,
        "lap_time_s": lap_time,
        "rows_converted": len(out_df),
        "csv_path": csv_path
    }


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 telemetry_converter.py <xrk_path> <csv_path> [lap_num]")
        sys.exit(1)
        
    x_path = sys.argv[1]
    c_path = sys.argv[2]
    l_num = int(sys.argv[3]) if len(sys.argv) > 3 else None
    
    res = convert_xrk_to_csv(x_path, c_path, l_num)
    print("Conversion complete:")
    for k, v in res.items():
        print(f"  {k}: {v}")
