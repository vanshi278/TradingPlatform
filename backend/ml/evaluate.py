"""Information Coefficient — the honest out-of-sample metric for a signal.

Per period, IC is the rank (Spearman) correlation between the predicted scores
and the realized forward returns across the cross-section. We report the mean IC,
its information ratio (mean/std), a t-stat, and the hit rate. A mean IC around
0.02–0.06 is a genuinely useful equity signal; anything claiming far more is
usually leaking.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


def _period_ic(group: pd.DataFrame) -> float:
    if len(group) < 3:
        return np.nan
    return spearmanr(group["pred"], group["fwd_ret"]).correlation


def ic_series(predictions: pd.DataFrame) -> pd.Series:
    """One IC per date."""
    if predictions.empty:
        return pd.Series(dtype=float)
    return predictions.groupby("date")[["pred", "fwd_ret"]].apply(_period_ic).dropna()


def ic_report(predictions: pd.DataFrame) -> dict:
    ics = ic_series(predictions)
    if ics.empty:
        return {}
    mean_ic = float(ics.mean())
    std_ic = float(ics.std(ddof=1)) if len(ics) > 1 else 0.0
    ic_ir = mean_ic / std_ic if std_ic > 0 else 0.0
    n = len(ics)
    return {
        "mean_ic": mean_ic,
        "std_ic": std_ic,
        "ic_ir": ic_ir,
        "t_stat": ic_ir * np.sqrt(n) if std_ic > 0 else 0.0,
        "hit_rate": float((ics > 0).mean()),
        "n_periods": n,
    }


def format_ic(name: str, rep: dict) -> str:
    if not rep:
        return f"{name:<16} (no IC)"
    return (
        f"{name:<16} mean IC {rep['mean_ic']:+.4f}  |  IC IR {rep['ic_ir']:+.2f}  |  "
        f"t {rep['t_stat']:+.2f}  |  hit {rep['hit_rate']:.0%}  |  n {rep['n_periods']}"
    )
