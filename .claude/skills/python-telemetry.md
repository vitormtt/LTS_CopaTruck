---
name: python-telemetry
description: |
  Protocol for ingesting, cleaning, and analysing motorsport telemetry data
  (MoTec .ld, CSV, HDF5). Activate when processing lap data, comparing setups,
  exporting analysis reports, or building data pipeline modules.
  Applies to SARU_LapAnalyzer and all LapTimeSimulator repos.
---

## Pipeline Stages

1. **Ingest** — identify format: MoTec .ld, CSV, Parquet, HDF5
2. **Validate** — check mandatory channels, sampling frequency, time gaps
3. **Synchronise** — align data by track distance (not wall-clock time)
4. **Clean** — outliers via IQR or physical threshold (e.g. `|ax| > 50 m/s²` → flag)
5. **Analyse** — pace, slip angle, brake balance, tyre load, mini-sector delta
6. **Export** — CSV + PNG (300 dpi) per analysis; HDF5 for structured datasets

## Mandatory Channels

| Channel | Unit | Notes |
|---------|------|-------|
| `vx` | m/s | Longitudinal speed |
| `ax` | m/s² | Longitudinal acceleration |
| `ay` | m/s² | Lateral acceleration |
| `steering_angle` | deg | |
| `lap_distance` | m | Primary alignment reference |
| `lap_time` | s | |

## Distance-Based Alignment (mandatory)

- All cross-lap and cross-setup comparisons must align on `lap_distance`, not time
- Resample to uniform distance grid before any delta computation
- Grid resolution: 1 m default, 0.5 m for high-precision sector analysis

## Output Standards

- CSV: `results/<circuit>_<date>_<analysis_type>.csv`
- PNG: `results/<circuit>_<date>_<analysis_type>.png` — 300 dpi, white background
- Never commit raw telemetry files to the repository (gitignore)

## Data Quality Flags

| Flag | Condition | Action |
|------|-----------|--------|
| `OUTLIER` | Value outside physical range | Replace with NaN, log warning |
| `GAP` | Missing data > 0.1 s | Log gap, do not interpolate silently |
| `SYNC_ERROR` | Distance non-monotonic | Raise exception before processing |
