"""
Setup optimization page component for the Streamlit UI.

Two optimizers over the VehicleSetup space (ARB front/rear, wing,
tyre pressure, brake bias):
- Grid Search: exhaustive over the discrete ARB/wing ranges;
- Differential Evolution (scipy): global stochastic search over all
  five setup variables with a convergence plot per generation.

Author: Lap Time Simulator Team
Date: 2026-06-06
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
from src.vehicle.units import bar_to_psi, psi_to_bar
from .helpers import cached_solver, fmt_laptime, init_session_state


def _evaluate_setup(base, circuit, arb_f: int, arb_r: int, wing: int,
                    pressure_bar: float, bias: float) -> float:
    """Lap time for one setup combination (inf when the solver fails)."""
    setup = VehicleSetup(
        arb_front=int(arb_f),
        arb_rear=int(arb_r),
        wing_position=int(wing),
        tyre_pressure=float(pressure_bar),
        brake_bias=float(bias),
        setup_name=f"ARB{int(arb_f)}/{int(arb_r)}_W{int(wing)}",
    )
    params = apply_setup(base, setup)
    params_dict = params.to_solver_dict()
    # apply_setup already folded the pressure grip delta into mu/Cf/Cr;
    # reset the exported cold pressure so it is not re-applied
    params_dict["P_cold_bar"] = 1.8
    try:
        r = cached_solver(params_dict=params_dict, circuit=circuit,
                          config={}, save_csv=False)
        return float(r["lap_time"])
    except Exception:
        return float("inf")


def _run_differential_evolution(base, circuit, pressure_bounds_bar,
                                bias_bounds, maxiter: int, popsize: int):
    """DE over [arb_f, arb_r, wing, pressure, bias]; returns history+best."""
    bounds = [(1, 7), (1, 7), (1, 9), pressure_bounds_bar, bias_bounds]
    history: list = []

    def objective(x: np.ndarray) -> float:
        arb_f, arb_r, wing = (int(round(v)) for v in x[:3])
        return _evaluate_setup(base, circuit, arb_f, arb_r, wing, x[3], x[4])

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


def optimization_page() -> None:
    st.header("Setup optimization")
    st.caption("Search the ARB / wing / pressure / bias space for the fastest setup.")
    init_session_state()

    if st.session_state.circuit is None:
        st.warning("Select a track on the Track page first.")
        return

    if st.session_state.vehicle_params is None or not st.session_state.params_saved:
        st.warning("Configure and save a vehicle on the Parameters page first.")
        return

    st.caption(
        "Grid-search over ARB front, ARB rear, and Wing position to find the "
        "optimum setup combination for this track. Tyre pressure and brake bias "
        "are kept constant. ARB levels map to roll stiffness (k_roll front/rear) "
        "and wing positions to aero deltas (ΔCd/ΔCl) applied on top of the "
        "selected truck's baseline parameters."
    )

    method = st.radio(
        "Optimization Method:",
        ["Grid Search", "Differential Evolution (scipy)"],
        horizontal=True, key="opt_method",
        help="Grid Search sweeps ARB/wing exhaustively with fixed "
             "pressure/bias. Differential Evolution searches all five "
             "setup variables (incl. pressure and bias) globally."
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
                pressure_bounds_bar=(psi_to_bar(20.5), psi_to_bar(34.5)),
                bias_bounds=(-2.0, 0.0),
                maxiter=int(de_maxiter), popsize=int(de_popsize),
            )
            elapsed = time.perf_counter() - t0

            arb_f, arb_r, wing = (int(round(v)) for v in result.x[:3])
            best_pressure, best_bias = float(result.x[3]), float(result.x[4])
            st.success(
                f"DE complete in {elapsed:.1f} s ({result.nfev} laps). "
                f"Optimum: **ARB {arb_f}/{arb_r}, wing {wing}, "
                f"{bar_to_psi(best_pressure):.1f} psi, bias {best_bias:+.1f}** "
                f"→ **{fmt_laptime(float(result.fun))}**"
            )

            fig_conv = go.Figure()
            fig_conv.add_trace(go.Scatter(
                y=history, mode="lines+markers", name="Best lap",
                line=dict(color="seagreen", width=2),
            ))
            fig_conv.update_layout(
                title="Convergence — best lap time per generation",
                xaxis_title="Generation", yaxis_title="Lap time (s)",
                height=320, margin=dict(l=0, r=0, t=40, b=0),
            )
            st.plotly_chart(fig_conv, width="stretch")
        return

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        pressure_psi = st.number_input(
            "Tyre Pressure (psi)", 20.5, 34.5, 26.0, step=0.5, key="opt_pressure"
        )
        pressure = psi_to_bar(pressure_psi)
        st.caption(f"= {pressure:.2f} bar")
    with col_p2:
        bias = st.slider("Brake Bias", -2.0, 0.0, -1.0, step=0.5, key="opt_bias")

    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1:
        arb_f_range = st.slider("ARB Front Range", 1, 7, (1, 7), key="opt_arb_f")
    with col_r2:
        arb_r_range = st.slider("ARB Rear Range", 1, 7, (1, 7), key="opt_arb_r")
    with col_r3:
        wing_range = st.slider("Wing Position Range", 1, 9, (1, 9), key="opt_wing")

    arb_f_vals = list(range(arb_f_range[0], arb_f_range[1] + 1))
    arb_r_vals = list(range(arb_r_range[0], arb_r_range[1] + 1))
    wing_vals = list(range(wing_range[0], wing_range[1] + 1))
    total = len(arb_f_vals) * len(arb_r_vals) * len(wing_vals)

    st.info(
        f"Total setup combinations to evaluate: **{total}** "
        f"(ARB Front: {len(arb_f_vals)} × ARB Rear: {len(arb_r_vals)} × Wing: {len(wing_vals)})"
    )

    if st.button("Run grid search", width="stretch", type="primary"):
        base = get_vehicle_by_id(st.session_state.vehicle_id)
        circuit = st.session_state.circuit
        results_opt = []

        bar = st.progress(0, text="Evaluating configurations...")
        t0 = time.perf_counter()

        for idx, (af, ar, w) in enumerate(product(arb_f_vals, arb_r_vals, wing_vals)):
            bar.progress(
                (idx + 1) / total,
                text=f"Combo {idx+1}/{total} — ARB {af}/{ar} | Wing {w}"
            )

            setup = VehicleSetup(
                arb_front=af,
                arb_rear=ar,
                wing_position=w,
                tyre_pressure=float(pressure),
                brake_bias=float(bias),
                setup_name=f"ARB{af}/{ar}_W{w}",
            )
            params = apply_setup(base, setup)
            params_dict = params.to_solver_dict()
            # apply_setup already folded the pressure-dependent grip
            # scaling into mu/Cf/Cr; reset the exported cold pressure to
            # the reference so the legacy path doesn't re-apply the delta
            params_dict["P_cold_bar"] = 1.8

            try:
                r = cached_solver(
                    params_dict=params_dict,
                    circuit=circuit,
                    config={},
                    save_csv=False
                )
                results_opt.append({
                    "arb_f": af,
                    "arb_r": ar,
                    "wing": w,
                    "lap_time": r["lap_time"],
                    "vmax_kmh": float(np.max(r["v_profile"])) * 3.6,
                    "vmean_kmh": float(np.mean(r["v_profile"])) * 3.6,
                })
            except Exception:
                results_opt.append({
                    "arb_f": af,
                    "arb_r": ar,
                    "wing": w,
                    "lap_time": float("inf"),
                    "vmax_kmh": 0.0,
                    "vmean_kmh": 0.0,
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
            f"Optimum: **ARB {int(best.arb_f)}/{int(best.arb_r)}, wing {int(best.wing)}** "
            f"→ **{fmt_laptime(best.lap_time)}**"
        )

        # Top 10 setups
        st.subheader("Top 10 fastest setups")
        top10 = valid_df.nsmallest(10, "lap_time").copy()
        top10["Lap Time"] = top10["lap_time"].apply(fmt_laptime)
        top10.columns = [c.replace("_", " ").title() for c in top10.columns]
        st.dataframe(top10, width="stretch")

        # Heatmaps — one per wing position
        st.subheader("Lap-time sensitivity — ARB front vs ARB rear")
        for w in wing_vals:
            sub = valid_df[valid_df["wing"] == w]
            if sub.empty:
                continue
            pivot = sub.pivot(index="arb_r", columns="arb_f", values="lap_time")
            
            fig_hm = go.Figure(go.Heatmap(
                z=pivot.values,
                x=[str(c) for c in pivot.columns],
                y=[str(r) for r in pivot.index],
                colorscale='RdYlGn_r',
                colorbar=dict(title='Lap (s)'),
                text=[[fmt_laptime(v) for v in row] for row in pivot.values],
                texttemplate="%{text}",
            ))
            fig_hm.update_layout(
                title=f'Wing Position = {w}',
                xaxis_title='ARB Front (Stiffness Level)',
                yaxis_title='ARB Rear (Stiffness Level)',
                height=350,
                margin=dict(l=0, r=0, t=40, b=0),
            )
            st.plotly_chart(fig_hm, width="stretch")
