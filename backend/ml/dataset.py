"""Build the cross-sectional monthly panel.

Each row is (month-end, symbol): the FEATURE_COLUMNS as of that month-end, plus
the realized forward 1-month return and its cross-sectional rank (the target).
Monthly sampling keeps the forward-return windows non-overlapping, so the IC
series is clean rather than autocorrelated.
"""
from __future__ import annotations

import pandas as pd

from ml.features import FEATURE_COLUMNS, compute_features


def _month_end_last(obj):
    """Resample to month-end, taking the last value. Robust to pandas freq alias."""
    try:
        return obj.resample("ME").last()
    except ValueError:
        return obj.resample("M").last()


def build_panel(bars: dict[str, pd.DataFrame], horizon_months: int = 1) -> pd.DataFrame:
    frames = []
    for sym, df in bars.items():
        df = df.sort_index()
        if len(df) < 260:                       # need ~1y warmup for the 252-day features
            continue
        monthly_feats = _month_end_last(compute_features(df))
        monthly_close = _month_end_last(df["close"])
        fwd_ret = monthly_close.shift(-horizon_months) / monthly_close - 1.0

        panel = monthly_feats.copy()
        panel["symbol"] = sym
        panel["fwd_ret"] = fwd_ret
        frames.append(panel)

    if not frames:
        return pd.DataFrame()

    full = pd.concat(frames)
    full = full.dropna(subset=[*FEATURE_COLUMNS, "fwd_ret"])
    full["date"] = full.index
    # cross-sectional rank of forward return per date, centered to [-0.5, +0.5]
    full["target"] = full.groupby("date")["fwd_ret"].rank(pct=True) - 0.5
    # keep months with a real cross-section to rank
    counts = full.groupby("date")["symbol"].transform("size")
    full = full[counts >= 5]
    return full.reset_index(drop=True)
