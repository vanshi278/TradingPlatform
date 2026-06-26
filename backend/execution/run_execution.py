"""Phase 5 demo (Milestone 3): TWAP vs VWAP vs Almgren-Chriss, compared by
implementation shortfall against a simulated limit order book.

    cd backend && python -m execution.run_execution

Executes the same parent order under each schedule over many random paths and
reports mean IS (the impact cost) and std IS (the timing risk). Almgren-Chriss
front-loading trades a little more mean cost for materially lower risk.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from execution.almgren_chriss import ac_trajectory
from execution.schedules import ac_schedule, twap_schedule, u_shaped_profile, vwap_schedule
from execution.simulator import monte_carlo_is

RESULTS = Path(__file__).resolve().parents[2] / "results"
# Almgren-Chriss model params (shape only): kappa = sqrt(lam * sigma^2 / eta)
SIGMA_AC, ETA, GAMMA = 0.02, 2e-6, 0.0
LAM_LOW, LAM_HIGH = 1e-3, 5e-2          # near-uniform vs strongly front-loaded


def build_schedules(X, T, N):
    return {
        "TWAP": twap_schedule(X, N),
        "VWAP (U-shape)": vwap_schedule(X, u_shaped_profile(N)),
        "AC (low λ)": ac_schedule(X, T, N, SIGMA_AC, ETA, GAMMA, lam=LAM_LOW),
        "AC (high λ)": ac_schedule(X, T, N, SIGMA_AC, ETA, GAMMA, lam=LAM_HIGH),
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Implementation-shortfall comparison")
    p.add_argument("--shares", type=int, default=50_000)
    p.add_argument("--slices", type=int, default=20)
    p.add_argument("--paths", type=int, default=200)
    args = p.parse_args()

    X, N, T = args.shares, args.slices, 1.0
    # perm_impact=0: in linear Almgren-Chriss permanent impact is schedule-
    # independent, so the trade-off we're showing is temporary impact vs. risk.
    sim_kw = dict(mid0=100.0, tick=0.05, sigma=0.0010, perm_impact=0.0,
                  liquidity_per_level=1500, levels=60)
    schedules = build_schedules(X, T, N)

    print(f"parent order: BUY {X:,} over {N} slices | {args.paths} Monte-Carlo paths\n")
    rows = []
    for name, sched in schedules.items():
        res = monte_carlo_is(sched, side="buy", n_paths=args.paths, **sim_kw)
        rows.append((name, res["mean_is_bps"], res["std_is_bps"]))

    print(f"{'schedule':<18}{'mean IS (bps)':>16}{'std IS / risk (bps)':>22}")
    print("-" * 56)
    for name, mean_is, std_is in rows:
        print(f"{name:<18}{mean_is:>16.2f}{std_is:>22.2f}")

    twap = next(r for r in rows if r[0] == "TWAP")
    ac_hi = next(r for r in rows if r[0].startswith("AC (high"))
    risk_cut = (1 - ac_hi[2] / twap[2]) * 100 if twap[2] else 0.0
    print(
        f"\nAC(high λ) vs TWAP: risk {twap[2]:.1f} -> {ac_hi[2]:.1f} bps "
        f"({risk_cut:.0f}% lower) for {ac_hi[1] - twap[1]:+.1f} bps mean cost"
    )
    _save_plots(X, T, N, rows)


def _save_plots(X, T, N, rows) -> None:
    RESULTS.mkdir(exist_ok=True)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        t = np.linspace(0, T, N + 1)
        fig, ax = plt.subplots(figsize=(9, 5))
        for lam, label in [(LAM_LOW, "AC low λ"), (LAM_HIGH, "AC high λ (front-loaded)")]:
            x, _ = ac_trajectory(X, T, N, SIGMA_AC, ETA, GAMMA, lam)
            ax.plot(t, x, marker="o", ms=3, label=label)
        ax.plot(t, X * (1 - t / T), "--", color="#999", label="uniform (TWAP)")
        ax.set_xlabel("time"); ax.set_ylabel("shares remaining"); ax.legend(); ax.grid(alpha=0.3)
        ax.set_title("Almgren-Chriss execution trajectories")
        fig.tight_layout(); fig.savefig(RESULTS / "ac_trajectories.png", dpi=110); plt.close(fig)

        fig, ax = plt.subplots(figsize=(7, 5))
        for name, mean_is, std_is in rows:
            ax.scatter(std_is, mean_is, s=60)
            ax.annotate(name, (std_is, mean_is), fontsize=8, xytext=(5, 5), textcoords="offset points")
        ax.set_xlabel("risk: std of IS (bps)"); ax.set_ylabel("mean IS (bps)")
        ax.set_title("execution: cost vs risk"); ax.grid(alpha=0.3)
        fig.tight_layout(); fig.savefig(RESULTS / "is_frontier.png", dpi=110); plt.close(fig)
    except Exception as exc:  # noqa: BLE001
        print(f"(plots skipped: {exc})")


if __name__ == "__main__":
    main()
