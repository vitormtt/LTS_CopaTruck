---
name: python-telemetry
description: |
  Protocol for ingesting, processing and analysing motorsport telemetry data
  (MoTec .ld, CSV, iRacing, ACC, custom formats). Activate when working on
  data pipelines, lap analysis, driver metrics, or KPI computation.
---

## Pipeline Stages

1. **Ingest**: identify format (MoTec .ld, CSV, Parquet, HDF5)
2. **Validate**: check mandatory channels, sampling rate, gaps, outliers
3. **Synchronise**: align all channels by distance (not time)
4. **Clean**: remove outliers via physical threshold (e.g. ax > 5g → suspect)
5. **Analyse**: compute KPIs, sector deltas, driver metrics
6. **Export**: CSV + PNG figure (300 dpi minimum) per analysis

## Mandatory Channels

| Channel | Unit | Notes |
|---------|------|-------|
| `vx` | m/s | longitudinal velocity |
| `ax`, `ay` | m/s² | longitudinal and lateral acceleration |
| `steering_angle` | deg | at steering wheel |
| `lap_distance` | m | preferred over lap_time for synchronisation |
| `gear` | int | current gear |

## Data Quality Rules

- Flag any sample where `sqrt(ax**2 + ay**2) > 5.0 * G` as outlier
- Resample to uniform distance grid (1 m spacing) before any analysis
- Never interpolate more than 5 consecutive missing samples — flag gap instead
- All channels must share the same distance axis before comparison

## Output Standards

- File naming: `<circuit>_<session>_<driver>_<YYYYMMDD>.csv`
- Figures: 300 dpi PNG, axes labelled with units, legend identifying each run
- Reports: Markdown with embedded figures in `reports/` or `docs/`
