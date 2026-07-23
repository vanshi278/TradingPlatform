"""LSTM sequence model — the neural-net alternative to LightGBM.

It consumes a *sequence* of the last `window` monthly feature vectors per symbol
and predicts the same cross-sectional forward-return rank target, so it plugs
into the exact same walk-forward CV and Information-Coefficient evaluation as the
tree model — an honest, apples-to-apples comparison on identical folds.

PyTorch is imported lazily so the package still imports without it (the pipeline
skips the LSTM and reports LightGBM/momentum only). Features are standardized
using train-fold statistics only (no leakage).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml.features import FEATURE_COLUMNS
from ml.walkforward import walk_forward_splits


def torch_available() -> bool:
    try:
        import torch  # noqa: F401
        return True
    except Exception:
        return False


def _month_key(d) -> str:
    return pd.Timestamp(d).strftime("%Y-%m")


def build_sequences(panel: pd.DataFrame, window: int = 6, feature_cols=FEATURE_COLUMNS):
    """Return (X[n, window, n_features], target[n], fwd_ret[n], end_dates[n], symbols[n]).

    Each sample is `window` consecutive monthly feature vectors for one symbol,
    labelled with that final month's target / forward return.
    """
    X, target, fwd, dates, syms = [], [], [], [], []
    for sym, g in panel.groupby("symbol"):
        g = g.sort_values("date")
        feats = g[feature_cols].to_numpy(dtype=np.float32)
        tgt = g["target"].to_numpy(dtype=np.float32)
        fr = g["fwd_ret"].to_numpy(dtype=np.float32)
        dts = list(g["date"])
        for i in range(window - 1, len(g)):
            X.append(feats[i - window + 1:i + 1])
            target.append(tgt[i])
            fwd.append(fr[i])
            dates.append(dts[i])
            syms.append(sym)
    return (np.asarray(X, dtype=np.float32), np.asarray(target, dtype=np.float32),
            np.asarray(fwd, dtype=np.float32), np.asarray([_month_key(d) for d in dates]),
            np.asarray(dates, dtype=object), np.asarray(syms))


def _train_lstm(x_tr, y_tr, hidden, layers, epochs, lr, seed):
    import torch
    import torch.nn as nn

    torch.manual_seed(seed)
    np.random.seed(seed)

    class LSTMRegressor(nn.Module):
        def __init__(self, n_features):
            super().__init__()
            self.lstm = nn.LSTM(n_features, hidden, layers, batch_first=True,
                                dropout=0.1 if layers > 1 else 0.0)
            self.head = nn.Linear(hidden, 1)

        def forward(self, x):
            out, _ = self.lstm(x)
            return self.head(out[:, -1, :]).squeeze(-1)

    model = LSTMRegressor(x_tr.shape[-1])
    xt = torch.tensor(x_tr)
    yt = torch.tensor(y_tr)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()
    n = xt.shape[0]
    batch = 128
    model.train()
    for _ in range(epochs):
        perm = torch.randperm(n)
        for s in range(0, n, batch):
            idx = perm[s:s + batch]
            opt.zero_grad()
            loss = loss_fn(model(xt[idx]), yt[idx])
            loss.backward()
            opt.step()
    return model


def walk_forward_predict_lstm(
    panel: pd.DataFrame,
    window: int = 6,
    min_train: int = 36,
    test_size: int = 12,
    hidden: int = 32,
    layers: int = 1,
    epochs: int = 30,
    lr: float = 1e-3,
    seed: int = 42,
) -> pd.DataFrame:
    """Out-of-sample LSTM predictions in the same shape as the LightGBM path:
    columns [date, symbol, pred, fwd_ret]."""
    import torch

    X, y, fwd, keys, dates, syms = build_sequences(panel, window)
    out = []
    for train_dates, test_dates in walk_forward_splits(panel["date"], min_train, test_size):
        train_keys = {_month_key(d) for d in train_dates}
        test_keys = {_month_key(d) for d in test_dates}
        tr = np.array([k in train_keys for k in keys])
        te = np.array([k in test_keys for k in keys])
        if tr.sum() < 50 or te.sum() == 0:
            continue

        # standardize features on train stats only (avoid leakage)
        flat = X[tr].reshape(-1, X.shape[-1])
        mu, sd = flat.mean(0), flat.std(0) + 1e-8
        x_tr = (X[tr] - mu) / sd
        x_te = (X[te] - mu) / sd

        model = _train_lstm(x_tr, y[tr], hidden, layers, epochs, lr, seed)
        model.eval()
        with torch.no_grad():
            preds = model(torch.tensor(x_te.astype(np.float32))).numpy()

        out.append(pd.DataFrame({
            "date": dates[te], "symbol": syms[te], "pred": preds, "fwd_ret": fwd[te],
        }))

    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(
        columns=["date", "symbol", "pred", "fwd_ret"]
    )
