"""Performance metrics from a portfolio equity curve: total return, CAGR,
annualized Sharpe, and max drawdown. Pure pandas/numpy (no plotting here)."""
from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def max_drawdown(total: pd.Series) -> float:
    """Most negative peak-to-trough decline (e.g. -0.23 == -23%)."""
    if total.empty:
        return 0.0
    running_max = total.cummax()
    drawdown = total / running_max - 1.0
    return float(drawdown.min())


def sharpe_ratio(returns: pd.Series, periods_per_year: int = TRADING_DAYS) -> float:
    r = returns.dropna()
    if len(r) < 2 or r.std(ddof=1) == 0:
        return 0.0
    return float(np.sqrt(periods_per_year) * r.mean() / r.std(ddof=1))


def compute_metrics(equity_df: pd.DataFrame, periods_per_year: int = TRADING_DAYS) -> dict:
    if equity_df.empty or "total" not in equity_df:
        return {}
    total = equity_df["total"].astype(float)
    returns = total.pct_change().dropna()
    n = len(total)

    total_return = float(total.iloc[-1] / total.iloc[0] - 1.0)
    cagr = float((total.iloc[-1] / total.iloc[0]) ** (periods_per_year / max(n - 1, 1)) - 1.0)

    return {
        "start_equity": float(total.iloc[0]),
        "end_equity": float(total.iloc[-1]),
        "total_return": total_return,
        "cagr": cagr,
        "sharpe": sharpe_ratio(returns, periods_per_year),
        "max_drawdown": max_drawdown(total),
        "n_periods": n,
    }


def format_metrics(metrics: dict) -> str:
    if not metrics:
        return "(no metrics — empty equity curve)"
    return (
        f"  start equity : {metrics['start_equity']:>14,.2f}\n"
        f"  end equity   : {metrics['end_equity']:>14,.2f}\n"
        f"  total return : {metrics['total_return']:>13.2%}\n"
        f"  CAGR         : {metrics['cagr']:>13.2%}\n"
        f"  Sharpe       : {metrics['sharpe']:>14.2f}\n"
        f"  max drawdown : {metrics['max_drawdown']:>13.2%}\n"
        f"  periods      : {metrics['n_periods']:>14d}"
    )
