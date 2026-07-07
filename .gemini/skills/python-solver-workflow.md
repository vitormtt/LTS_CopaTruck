---
name: python-solver-workflow
description: |
  Protocol for implementing, validating and debugging the Two-Pass lap time
  solver used across all SARU simulators. Activate when working on solver
  logic, pass algorithms, grip limits, or cross-validation against reference
  lap times.
---

## Two-Pass Solver Overview

```
Forward pass  →  max acceleration at each track point
                  constraint: traction circle + lateral velocity limit
Backward pass →  max braking at each corner entry
                  constraint: not exceeding corner speed from downstream
Result        →  velocity profile v(s) over full lap distance s
```

## Implementation Rules

- Never alter pass logic without cross-validating against at least one known lap time
- Grip limit must be computed from friction circle: `a_total = sqrt(ax**2 + ay**2) <= mu * g`
- Gear selection must maintain RPM within engine band — never hardcode gear changes
- Aero drag: always applied in forward pass; lift (if any) affects normal force and grip

## Validation Protocol

1. Select reference circuit with known lap time (±0.5 s tolerance)
2. Run solver with default vehicle preset
3. Compare predicted vs reference: lap time, speed trace, sector times
4. If delta > 0.5 s: investigate grip model, aero model, gear selection in that order
5. Document result in `docs/validation_<circuit>_<date>.md`

## Debug Checklist

- [ ] Velocity profile physically plausible (no negative speed, no jumps > 50 km/h/step)
- [ ] Friction circle not exceeded at any point
- [ ] Engine RPM within band at all gear changes
- [ ] HDF5 track geometry loaded correctly (check centerline continuity)
- [ ] Backward pass terminal condition: entry speed ≤ maximum corner speed

## Cross-Project Compatibility

The two-pass method is identical across CopaTruck, StockCar, Generic and SARU simulators.
Any fix or improvement to the solver algorithm must be propagated to all active repos.
