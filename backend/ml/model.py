"""Model factory + the walk-forward out-of-sample prediction loop.

Primary model is LightGBM; if it can't load (e.g. libomp missing on macOS) we
fall back to scikit-learn's GradientBoostingRegressor so the pipeline always
runs. Both are tree models, so SHAP's TreeExplainer works on either.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml.features import FEATURE_COLUMNS
from ml.walkforward import walk_forward_splits


def make_model(seed: int = 42):
    """Return (name, estimator)."""
    try:
        import lightgbm as lgb

        model = lgb.LGBMRegressor(
            n_estimators=300, num_leaves=31, learning_rate=0.03,
            subsample=0.8, colsample_bytree=0.8, random_state=seed, verbose=-1,
        )
        return "lightgbm", model
    except Exception:
        from sklearn.ensemble import GradientBoostingRegressor

        model = GradientBoostingRegressor(
            n_estimators=200, max_depth=3, learning_rate=0.05, subsample=0.8, random_state=seed,
        )
        return "sklearn-gbr", model


def walk_forward_predict(
    panel: pd.DataFrame,
    min_train: int = 36,
    test_size: int = 12,
    seed: int = 42,
) -> tuple[pd.DataFrame, str]:
    """Fit fold-by-fold and collect out-of-sample predictions.

    Returns (predictions, model_name) where predictions has columns
    [date, symbol, pred, fwd_ret].
    """
    name, _ = make_model(seed)
    dates = panel["date"].to_numpy()
    out = []
    for train_dates, test_dates in walk_forward_splits(panel["date"], min_train, test_size):
        train = panel[panel["date"].isin(train_dates)]
        test = panel[panel["date"].isin(test_dates)]
        if train.empty or test.empty:
            continue
        _, model = make_model(seed)
        model.fit(train[FEATURE_COLUMNS], train["target"])
        preds = model.predict(test[FEATURE_COLUMNS])
        out.append(pd.DataFrame({
            "date": test["date"].to_numpy(),
            "symbol": test["symbol"].to_numpy(),
            "pred": preds,
            "fwd_ret": test["fwd_ret"].to_numpy(),
        }))
    predictions = pd.concat(out, ignore_index=True) if out else pd.DataFrame(
        columns=["date", "symbol", "pred", "fwd_ret"]
    )
    return predictions, name


def momentum_baseline(panel: pd.DataFrame, feature: str = "ret_126") -> pd.DataFrame:
    """Baseline 'prediction' = a single momentum feature, scored over the same
    test months the model is evaluated on (folds after min_train)."""
    dates = sorted(panel["date"].unique())
    test_dates = set(dates[36:])  # mirror the default min_train=36
    sub = panel[panel["date"].isin(test_dates)]
    return pd.DataFrame({
        "date": sub["date"].to_numpy(),
        "symbol": sub["symbol"].to_numpy(),
        "pred": sub[feature].to_numpy(),
        "fwd_ret": sub["fwd_ret"].to_numpy(),
    })
