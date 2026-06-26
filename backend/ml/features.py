"""Per-symbol technical features for the forecasting model.

Every feature at time t uses only information available at or before t (rolling
windows include the current bar but never future bars), so the feature matrix
carries no lookahead. The forward-return *target* is built separately in
dataset.py.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# 18 features — returns, volatility, RSI, volume, trend, mean-reversion, range.
FEATURE_COLUMNS = [
    "ret_1", "ret_5", "ret_10", "ret_21", "ret_63", "ret_126",
    "vol_21", "vol_63",
    "rsi_14",
    "vol_ratio_21",
    "close_sma20", "close_sma50", "sma20_sma50",
    "zscore_20",
    "hi_252", "lo_252",
    "ret_skew_21", "mom_21_5",
]


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0).rolling(window).mean()
    down = (-delta.clip(upper=0)).rolling(window).mean()
    rs = up / down.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    """df: one symbol's daily OHLCV (UTC index). Returns the FEATURE_COLUMNS frame."""
    close = df["close"]
    volume = df["volume"]
    ret1 = close.pct_change()

    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()

    f = pd.DataFrame(index=df.index)
    f["ret_1"] = ret1
    f["ret_5"] = close.pct_change(5)
    f["ret_10"] = close.pct_change(10)
    f["ret_21"] = close.pct_change(21)
    f["ret_63"] = close.pct_change(63)
    f["ret_126"] = close.pct_change(126)
    f["vol_21"] = ret1.rolling(21).std()
    f["vol_63"] = ret1.rolling(63).std()
    f["rsi_14"] = rsi(close, 14)
    f["vol_ratio_21"] = volume / volume.rolling(21).mean()
    f["close_sma20"] = close / sma20 - 1
    f["close_sma50"] = close / sma50 - 1
    f["sma20_sma50"] = sma20 / sma50 - 1
    f["zscore_20"] = (close - sma20) / close.rolling(20).std()
    f["hi_252"] = close / close.rolling(252).max() - 1
    f["lo_252"] = close / close.rolling(252).min() - 1
    f["ret_skew_21"] = ret1.rolling(21).skew()
    f["mom_21_5"] = close.pct_change(21) - close.pct_change(5)
    return f[FEATURE_COLUMNS]
