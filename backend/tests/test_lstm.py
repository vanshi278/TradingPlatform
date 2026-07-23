"""LSTM sequence model — sequence building + walk-forward prediction.
The training test skips automatically if torch isn't installed."""
import numpy as np
import pandas as pd
import pytest

from ml.features import FEATURE_COLUMNS
from ml.lstm_model import build_sequences, walk_forward_predict_lstm


def _synthetic_panel(n_months=42, n_syms=10, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2016-01-31", periods=n_months, freq="ME", tz="UTC")
    rows = []
    for s in range(n_syms):
        for d in dates:
            feat = {c: float(rng.normal()) for c in FEATURE_COLUMNS}
            # forward return partly driven by a feature so a model can learn signal
            fwd = 0.6 * feat["ret_21"] + rng.normal(0, 0.5)
            rows.append({**feat, "date": d, "symbol": f"S{s}", "fwd_ret": fwd})
    panel = pd.DataFrame(rows)
    panel["target"] = panel.groupby("date")["fwd_ret"].rank(pct=True) - 0.5
    return panel


def test_build_sequences_shapes():
    panel = _synthetic_panel(n_months=20, n_syms=4)
    X, y, fwd, keys, dates, syms = build_sequences(panel, window=6)
    assert X.ndim == 3
    assert X.shape[1] == 6                      # window
    assert X.shape[2] == len(FEATURE_COLUMNS)   # 22 features
    assert len(y) == len(fwd) == len(syms) == X.shape[0]
    # a window of 6 over 20 months => 15 sequences per symbol * 4 symbols
    assert X.shape[0] == 15 * 4


def test_lstm_walk_forward_predicts():
    pytest.importorskip("torch")
    panel = _synthetic_panel()
    preds = walk_forward_predict_lstm(
        panel, window=6, min_train=24, test_size=9, hidden=16, epochs=5, seed=0
    )
    assert set(preds.columns) == {"date", "symbol", "pred", "fwd_ret"}
    assert len(preds) > 0
    assert np.isfinite(preds["pred"].to_numpy()).all()


def test_lstm_learns_signal_positive_ic():
    """On a panel where the target is driven by a feature, OOS IC should be > 0."""
    pytest.importorskip("torch")
    from ml.evaluate import ic_report

    panel = _synthetic_panel(n_months=48, n_syms=12, seed=1)
    preds = walk_forward_predict_lstm(
        panel, window=6, min_train=24, test_size=12, hidden=24, epochs=20, seed=1
    )
    rep = ic_report(preds)
    assert rep["mean_ic"] > 0                    # captured the injected signal
