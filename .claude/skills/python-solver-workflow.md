---
name: python-solver-workflow
description: |
  Rules and validation protocol for the SARU two-pass lap time solver.
  Activate when modifying solver logic, adding vehicle parameters, changing
  tire model, or validating simulation results against known lap times.
  Applies to LapTimeSimulator_CopaTruck, LapTimeSimulator_StockCar,
  LapTimeSimulator_Generic, LapTimeSimulator_SARU.
---

## Two-Pass Solver — Core Rules

1. **Forward pass**: maximum acceleration at each point, limited by traction circle and lateral velocity
2. **Backward pass**: minimum braking speed to not exceed corner entry speed
3. **Never alter the two-pass method without cross-validation against a known reference lap time.**
4. If modifying solver: present proposed change + expected delta lap time before editing

## Validation Protocol

Before any solver change is committed:
1. Run baseline simulation → record reference lap time
2. Apply change
3. Run post-change simulation → compare lap time delta
4. Acceptable regression: ≤ 0.1 s on reference circuit
5. If delta > 0.1 s → flag as regression, revert and re-analyse

## Vehicle Parameter Protocol

- Vehicle parameters: loaded exclusively from `data/vehicles/<name>.json` or `.yaml`
- Never hardcode mass, Cf, Cr, Cd, gear ratios or brake balance in Python source
- New vehicle: implement via VehicleParams dataclass → save to `data/vehicles/`
- Parameter change: update JSON/YAML → re-run validation

## Track Protocol

- Track geometry: loaded from `tracks/<name>.hdf5` or `data/tracks/<name>.yaml`
- Never embed centerline coordinates or sector boundaries in Python source
- New circuit: use CircuitData + appropriate writer class

## Subsystem Swap Protocol

To swap tire model or solver implementation:
1. Verify ABC interface is fully implemented
2. Run existing test suite — must pass 100%
3. Run cross-validation on reference circuit
4. Update CLAUDE.md with new subsystem entry

## Prohibited Modifications

- Do not add `if category == ...` branching inside core solver
- Do not read files inside solver methods — pass pre-loaded data as arguments
- Do not cache simulation state between calls without explicit design review
