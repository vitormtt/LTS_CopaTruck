"""
Setup optimization page component for the Streamlit UI.

Searches the setup variables that actually move lap time in the point-mass
QSS solver — **wing position** (ΔCd/ΔCl) and **cold tyre pressure** (static
grip scaling):

- Grid Search: exhaustive over wing × pressure, with a lap-time heatmap;
- Differential Evolution (scipy): global search over [wing, pressure] with
  a convergence plot per generation.

Anti-roll bar balance and brake bias are held neutral: in a point-mass QSS
model they do not change peak grip (the loaded axle saturates near the same
floor regardless of roll-stiffness balance, and braking is grip-limited, not
bias-limited). They belong to the transient 14-DOF model — see the roadmap
note on the page.

Author: Lap Time Simulator Team
Date: 2026-06-06 (reworked 2026-07-06)
"""
import time
from itertools import product

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from scipy.optimize import differential_evolution

from src.vehicle.fleet import get_vehicle_by_id
from src.vehicle.setup import VehicleSetup, apply_setup
from src.vehicle.units import bar_to_psi
from .helpers import cached_solver, fmt_laptime, init_session_state
from src.visualization.theme import ACCENT

# Neutral, non-lap-affecting knobs held constant during optimization.
_NEUTRAL_ARB = 4
_NEUTRAL_BIAS = -1.0
# Cold tyre pressure search window [bar] (safe truck setup range, see setup.py).
_PRESSURE_MIN_BAR = 6.55
_PRESSURE_MAX_BAR = 8.62


def _evaluate_setup(base, circuit, wing: int, pressure_bar: float) -> float:
    """Lap time for one (wing, pressure) setup (inf when the solver fails)."""
    setup = VehicleSetup(
        arb_front=_NEUTRAL_ARB,
        arb_rear=_NEUTRAL_ARB,
        wing_position=int(wing),
        tyre_pressure=float(np.clip(pressure_bar, _PRESSURE_MIN_BAR,
                                    _PRESSURE_MAX_BAR)),
        brake_bias=_NEUTRAL_BIAS,
        setup_name=f"W{int(wing)}_P{pressure_bar:.2f}",
    )
    params = apply_setup(base, setup)
    params_dict = params.to_solver_dict()
    # apply_setup already folded the pressure grip delta into mu/Cf/Cr;
    # reset the exported cold pressure to the reference so it is not
    # re-applied downstream (delta = 0 at the reference).
    params_dict["P_cold_bar"] = 7.58
    try:
        r = cached_solver(params_dict=params_dict, circuit=circuit,
                          config={}, save_csv=False)
        return float(r["lap_time"])
    except Exception:
        return float("inf")


def _run_differential_evolution(base, circuit, wing_bounds, pressure_bounds_bar,
                                maxiter: int, popsize: int):
    """DE over [wing, pressure]; returns the scipy result and history."""
    bounds = [wing_bounds, pressure_bounds_bar]
    history: list = []

    def objective(x: np.ndarray) -> float:
        return _evaluate_setup(base, circuit, int(round(x[0])), x[1])

    progress = st.progress(0, text="Differential evolution...")

    def callback(xk, convergence=0.0):
        history.append(objective(xk))
        progress.progress(
            min(len(history) / maxiter, 1.0),
            text=f"Generation {len(history)}/{maxiter} — "
                 f"best {fmt_laptime(min(history))}"
        )

    result = differential_evolution(
        objective, bounds=bounds, maxiter=maxiter, popsize=popsize,
        seed=42, polish=False, callback=callback, tol=1e-6,
    )
    progress.empty()
    return result, history


def _roadmap_note() -> None:
    """Explain why ARB and brake bias are not optimization variables."""
    st.caption(
        "Only **wing** and **tyre pressure** are searched — the two setup "
        "knobs that move lap time in this point-mass QSS model. Anti-roll "
        "bar balance and brake bias affect transient handling (turn-in, "
        "mid-corner), which needs the transient 14-DOF model — roadmap item, "
        "held neutral here."
    )


def optimization_page() -> None:
    st.header("Setup optimization")
    st.caption("Search the wing / tyre-pressure space for the fastest setup.")
    init_session_state()

    if st.session_state.circuit is None:
        st.warning("Select a track on the Track page first.")
        return

    if st.session_state.vehicle_params is None or not st.session_state.params_saved:
        st.warning("Configure and save a vehicle on the Parameters page first.")
        return

    _roadmap_note()

    method = st.radio(
        "Optimization Method:",
        ["Grid Search", "Differential Evolution (scipy)"],
        horizontal=True, key="opt_method",
        help="Grid Search sweeps wing × pressure exhaustively. Differential "
             "Evolution searches the same space globally and stochastically."
    )

    if method == "Differential Evolution (scipy)":
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            de_maxiter = st.number_input(
                "Generations (maxiter)", 5, 100, 15, step=5, key="opt_de_iter"
            )
        with col_d2:
            de_popsize = st.number_input(
                "Population Size", 6, 40, 12, step=2, key="opt_de_pop"
            )

        if st.button("Run differential evolution", width="stretch",
                     type="primary"):
            base = get_vehicle_by_id(st.session_state.vehicle_id)
            circuit = st.session_state.circuit
            t0 = time.perf_counter()
            result, history = _run_differential_evolution(
                base, circuit,
                wing_bounds=(1, 9),
                pressure_bounds_bar=(_PRESSURE_MIN_BAR, _PRESSURE_MAX_BAR),
                maxiter=int(de_maxiter), popsize=int(de_popsize),
            )
            elapsed = time.perf_counter() - t0

            best_wing = int(round(result.x[0]))
            best_pressure = float(result.x[1])
            st.success(
                f"DE complete in {elapsed:.1f} s ({result.nfev} laps). "
                f"Optimum: **wing {best_wing}, "
                f"{bar_to_psi(best_pressure):.1f} psi "
                f"({best_pressure:.2f} bar)** "
                f"→ **{fmt_laptime(float(result.fun))}**"
            )

            fig_conv = go.Figure()
            fig_conv.add_trace(go.Scatter(
                y=history, mode="lines+markers", name="Best lap",
                line=dict(color=ACCENT, width=2),
            ))
            fig_conv.update_layout(
                title="Convergence — best lap time per generation",
                xaxis_title="Generation", yaxis_title="Lap time (s)",
                height=320, margin=dict(l=0, r=0, t=40, b=0),
            )
            st.plotly_chart(fig_conv, width="stretch")
        return

    # --- Grid search: wing × pressure ---
    col_w, col_p = st.columns(2)
    with col_w:
        wing_range = st.slider("Wing Position Range", 1, 9, (1, 9),
                               key="opt_wing")
    with col_p:
        n_pressure = st.slider("Pressure Steps", 3, 11, 6, key="opt_press_steps")

    wing_vals = list(range(wing_range[0], wing_range[1] + 1))
    pressure_vals = np.linspace(_PRESSURE_MIN_BAR, _PRESSURE_MAX_BAR, n_pressure)
    total = len(wing_vals) * len(pressure_vals)

    st.info(
        f"Total setup combinations to evaluate: **{total}** "
        f"(Wing: {len(wing_vals)} × Pressure: {len(pressure_vals)})"
    )

    if st.button("Run grid search", width="stretch", type="primary"):
        base = get_vehicle_by_id(st.session_state.vehicle_id)
        circuit = st.session_state.circuit
        results_opt = []

        bar = st.progress(0, text="Evaluating configurations...")
        t0 = time.perf_counter()

        for idx, (w, pr) in enumerate(product(wing_vals, pressure_vals)):
            bar.progress(
                (idx + 1) / total,
                text=f"Combo {idx+1}/{total} — wing {w} | {pr:.2f} bar"
            )
            lap = _evaluate_setup(base, circuit, w, pr)
            results_opt.append({
                "wing": w,
                "pressure_bar": round(float(pr), 3),
                "pressure_psi": round(bar_to_psi(float(pr)), 1),
                "lap_time": lap,
            })

        elapsed = time.perf_counter() - t0
        bar.empty()

        df_opt = pd.DataFrame(results_opt)
        valid_df = df_opt[df_opt["lap_time"] < float("inf")]

        if valid_df.empty:
            st.error("All setup configurations failed to solve.")
            return

        best = valid_df.loc[valid_df["lap_time"].idxmin()]
        st.success(
            f"Grid search complete in {elapsed:.1f} s. "
            f"Optimum: **wing {int(best.wing)}, {best.pressure_psi:.1f} psi "
            f"({best.pressure_bar:.2f} bar)** "
            f"→ **{fmt_laptime(best.lap_time)}**"
        )

        st.subheader("Top 10 fastest setups")
        top10 = valid_df.nsmallest(10, "lap_time").copy()
        top10["Lap Time"] = top10["lap_time"].apply(fmt_laptime)
        top10 = top10[["wing", "pressure_psi", "pressure_bar", "Lap Time"]]
        top10.columns = ["Wing", "Pressure (psi)", "Pressure (bar)", "Lap Time"]
        st.dataframe(top10, width="stretch", hide_index=True)

        st.subheader("Lap-time sensitivity — wing vs tyre pressure")
        pivot = valid_df.pivot(index="pressure_psi", columns="wing",
                               values="lap_time")
        fig_hm = go.Figure(go.Heatmap(
            z=pivot.values,
            x=[str(c) for c in pivot.columns],
            y=[f"{r:.0f}" for r in pivot.index],
            colorscale="RdYlGn_r",
            colorbar=dict(title="Lap (s)"),
            text=[[fmt_laptime(v) for v in row] for row in pivot.values],
            texttemplate="%{text}",
        ))
        fig_hm.update_layout(
            title="Lap time (s)",
            xaxis_title="Wing Position",
            yaxis_title="Tyre Pressure (psi)",
            height=400,
            margin=dict(l=0, r=0, t=40, b=0),
        )
        st.plotly_chart(fig_hm, width="stretch")
