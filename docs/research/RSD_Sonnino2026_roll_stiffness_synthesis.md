# Roll Stiffness Distribution & Handling Balance — Sonnino et al. 2026

> **Source:** S. Sonnino, S. Melzi, F. Pirchio, P. Caresia, A. Manzoni, G. Vaini,
> *"Active control of vehicle lateral dynamics through roll stiffness distribution:
> Simulation and driver-in-the-loop testing"*, **Control Engineering Practice 168 (2026) 106735**.
> Politecnico di Milano (Dept. Mech. Eng.) + Brembo R&D. Open access, CC-BY.
> DOI: 10.1016/j.conengprac.2025.106735 · PDF in `docs/research/1-s2.0-S0967066125004964-main.pdf`.
>
> **One-line takeaway:** the paper formalizes how **Roll Stiffness Distribution (RSD)**
> apportions lateral load transfer between axles and thereby sets the understeer/oversteer
> balance. **Our LTS solver already implements its core equation** ([lap_time_solver.py:680](../../src/simulation/lap_time_solver.py)) —
> so this paper *validates* our physics and *authoritatively explains* the long-standing
> "ARB is inert in lap time" finding, rather than exposing a bug to fix.

---

## 1. What the paper does

Active management of **Roll Stiffness Distribution (RSD)** via an **Active Anti-Roll Bar (AARB)**
to shift handling balance in real time. Control = feedforward baseline RSD (driver tuning `λ`)
+ yaw-rate-error feedback (mitigate under/oversteer). Tuned with a Genetic Algorithm; validated
on a 14-DoF model (VI-CarRealTime), then **driver-in-the-loop with 24 drivers** on the PoliMi
DriSMi simulator over ISO maneuvers. Also integrates Active Rear Steering (ARS, via LQR) and
maps the two systems' complementary domains.

## 2. Core physics (what matters for us)

**Roll Stiffness Distribution** — front roll stiffness over total (susp spring + ARB), Eq (1):

```
RSD = (k_susp,f + k_arb,f) / (k_susp,f + k_arb,f + k_susp,r + k_arb,r)
```

**Lateral load transfer apportioned by RSD** — Eq (3), the crown jewel:

```
ΔF_z,f = RSD       · (m · a_y · h_G / t)
ΔF_z,r = (1 − RSD) · (m · a_y · h_G / t)
```

with `h_G` = CG height, `t` = track, `a_y` = lateral acceleration.

**Balance mechanism** (§2.4, Fig. 1): tire lateral force saturates with vertical load, so load
transfer makes an axle's *summed* two-tire force fall **below** the idealized single-tire curve
(the inner-tire loss exceeds the outer-tire gain). Therefore:

- **↑ front RSD → more front load transfer → less front grip → understeer.**
- **↑ rear RSD (↓ front) → more rear load transfer → less rear grip → oversteer.**

**Yaw-rate reference** (handling target, single-track), Eq (7)–(8):

```
ψ_ref = v / ( l · (1 + K_us · v²) ) · δ        (linear range)
ψ_max = μ · g / v                              (friction-limited cap)
```

## 3. KEY: our solver already implements Eq (3)

`_axle_grip()` in [lap_time_solver.py:675-682](../../src/simulation/lap_time_solver.py) does exactly this:

```python
k_total = k_roll_front + k_roll_rear
frac_f  = k_roll_front / k_total          # == RSD
lat_moment = m_cur * |a_lat| * h_cg       # == m · a_y · h_G
dfz_f = lat_moment / tw_f * frac_f        # == ΔF_z,f  (Eq 3, front)
dfz_r = lat_moment / tw_r * (1 - frac_f)  # == ΔF_z,r  (Eq 3, rear)
```

Matches Eq (3) exactly, and our **per-axle track** (`tw_f`, `tw_r`) is finer than the paper's
single-track form. The nonlinear-tire balance effect is carried by the load-sensitivity factor
`_S_LOAD` (`ls_f`, `ls_r`, lines 731-732): higher axle load transfer → lower axle μ. Direction
matches the paper (↑ front RSD → `ls_f` down → understeer). **Our roll-balance physics is correct.**

## 4. This resolves the "ARB is inert in lap time" finding

SPM (2026-07-06) recorded: *"ARB is intrinsically inert in the lap time of a point-mass QSS solver."*
The paper explains and quantifies **why**, with a citable source:

- The **steady-state** gain from roll stiffness is small: ramp-steer max lateral accel improved only
  **+7.59%** even with *active* AARB at `λ=1.5` (+50% ARB). In a point-mass QSS the corner speed is
  set by the **combined** axle grip limit, so shifting a few % of load transfer between axles barely
  moves the *limiting* axle → barely moves lap time. Consistent with our finding.
- ARB's real payoff is **transient**: yaw-rate settling time **−72.64%**, sine-with-dwell yaw/sideslip
  overshoot **−71.59% / −22.25%**, roll angle down. These live in the **transient** domain a QSS
  point-mass cannot see.

**Conclusion:** ARB being flat in our lap time is *physically correct*, not a modeling gap. Making it
matter requires modeling transient yaw/roll dynamics (3DOF+ → 14DOF), i.e. **saru-core territory**,
not a QSS patch.

## 5. SARU umbrella — per-product implications

- **lts-copatruck (this repo, QSS "advanced sim"):** physics *confirmed* — no change needed to the
  load-transfer split. The `_yaw_speed_cap` (Iz quasi-transient) is our only lever on transient
  balance; the paper's yaw-rate reference + settling-time KPIs are a validation target if we extend it.
  Cheap win available: expose an **under/oversteer-balance telemetry channel** (front vs rear
  utilization from `mu_f·Fz_f` vs `mu_r·Fz_r`) — same "derived channel" pattern as `brake_lockup`,
  zero solver risk, makes RSD tuning visible even if it barely moves lap time.
- **saru-core (14-DoF transient IP):** the paper is a direct blueprint. Its 14-DoF model (Cheli 2006),
  AARB actuation, feedforward `λ` + yaw-rate feedback control, and LQR ARS (Eq 17-21) are exactly the
  transient/active layer where ARB *does* move the needle. This is where roll-stiffness control earns
  its keep.
- **saru-os (telemetry validation):** the ISO maneuver + KPI framework is a ready-made handling-validation
  harness — **Ramp Steer (ISO 4138)**, **Step Steer (ISO 7401)**, **Sine-with-Dwell (ISO 19365)** with
  KPIs (yaw-rate settling, sideslip β, roll angle, lateral-accel). Use for real-vs-sim handling checks.
- **Hase (simple QSS, Pérez):** already inherits the correct Eq (3) split (shared lineage). No action.
- **Driver-model frontier (#10 work):** the yaw-rate reference (Eq 7-9) is a clean handling *target* for
  a future adaptive driver model; the DiL methodology (24 drivers, ISO 3888-2 double-lane-change,
  objective + subjective KPIs) is a template for validating driver realism.

## 6. Concrete opportunities (flagged — none applied; guardrailed)

1. **Balance telemetry channel** (lts-copatruck) — derived front/rear grip-utilization + a static
   understeer-gradient readout from RSD. Non-solver, safe, makes ARB/RSD tuning legible. *Candidate now.*
2. **Yaw-rate-reference handling target** — adopt `ψ_ref` (Eq 7-8) with an understeer coefficient
   `K_us` derived from RSD for a transient balance model. *Changes the solver → measure + validate.*
3. **ISO handling-validation harness** (saru-os) — script the three maneuvers + KPIs.
4. **Active-ARB / active-setup roadmap** (saru-core) — the FF+FB control as a future differentiator.

## 7. Caveats

- Test vehicle is a **1987 kg electric sedan** (h_cg 0.53 m, track 1.44 m), not a 4950 kg truck
  (h_cg 1.1 m) — the *mechanism* generalizes but the *magnitudes* do not. A tall, narrow truck has
  much larger `m·a_y·h_G/t`, so load transfer (and its balance leverage) is proportionally larger.
- The paper is about **active** control; our presets are **passive/setup**. We consume the same
  load-transfer physics but tune RSD statically via `k_roll_front/k_roll_rear`.
- Their steady-state numbers come from a full transient tire model (Pacejka MF + relaxation); our
  `_S_LOAD` is a linear load-sensitivity proxy — adequate for QSS, not a transient substitute.
