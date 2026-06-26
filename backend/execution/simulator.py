"""Execute a schedule against the simulated LOB and measure implementation
shortfall (Phase 5.7 / 5.8).

Each slice: the mid first random-walks (timing risk), fresh resting liquidity is
laid around it, then the child order is sent as a market order that walks the
book (impact). Our own trading also permanently nudges the mid. Implementation
shortfall is the volume-weighted execution price vs the arrival mid, in bps.

The Almgren-Chriss trade-off falls straight out: front-loading (high lambda)
pays MORE impact (bigger early slices walk deeper) but LESS timing risk (the book
is done sooner, so the random walk has less time to move the average), hence
lower IS variance than uniform TWAP.
"""
from __future__ import annotations

import numpy as np

from execution.flow import OrderFlowGenerator
from execution.order_book import LimitOrderBook


def execute_schedule(
    schedule,
    side: str = "buy",
    mid0: float = 100.0,
    tick: float = 0.05,
    sigma: float = 0.0008,
    perm_impact: float = 2e-6,
    liquidity_per_level: int = 1000,
    levels: int = 100,
    seed=None,
):
    """Return (avg_exec_price, arrival_mid, total_qty)."""
    rng = np.random.default_rng(seed)
    flow = OrderFlowGenerator(tick=tick, seed=seed)
    arrival_mid = mid0
    mid = mid0
    total_cost = 0.0
    total_qty = 0

    for q in schedule:
        q = int(round(q))
        if q <= 0:
            continue
        mid *= float(np.exp(rng.normal(0.0, sigma)))            # timing risk
        book = LimitOrderBook()
        flow.seed_book(book, round(mid / tick) * tick, levels=levels, per_level=liquidity_per_level)
        fills = book.market_order(side, q)
        filled = sum(f.qty for f in fills)
        if filled:
            total_cost += sum(f.price * f.qty for f in fills)
            total_qty += filled
        signed = filled if side == "buy" else -filled
        mid += perm_impact * signed * mid                       # our permanent impact

    avg_price = total_cost / total_qty if total_qty else arrival_mid
    return avg_price, arrival_mid, total_qty


def implementation_shortfall_bps(avg_price, arrival_mid, side="buy") -> float:
    """Cost vs arrival mid in bps (positive = worse execution)."""
    diff = (avg_price - arrival_mid) if side == "buy" else (arrival_mid - avg_price)
    return diff / arrival_mid * 1e4


def monte_carlo_is(schedule, side="buy", n_paths=300, base_seed=0, **kwargs) -> dict:
    """Mean and std of implementation shortfall (bps) across random paths."""
    shortfalls = []
    for i in range(n_paths):
        avg, arrival, _qty = execute_schedule(schedule, side=side, seed=base_seed + i, **kwargs)
        shortfalls.append(implementation_shortfall_bps(avg, arrival, side))
    arr = np.array(shortfalls)
    return {
        "mean_is_bps": float(arr.mean()),
        "std_is_bps": float(arr.std(ddof=1)),
        "n_paths": len(arr),
    }
