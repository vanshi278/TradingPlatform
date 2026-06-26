import numpy as np
import pandas as pd

from ml.features import FEATURE_COLUMNS, compute_features


def _df(n=400, seed=0):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    idx = pd.date_range("2020-01-01", periods=n, freq="D", tz="UTC")
    return pd.DataFrame(
        {"open": close, "high": close * 1.01, "low": close * 0.99, "close": close, "volume": 1e6},
        index=idx,
    )


def test_feature_columns_present_and_ordered():
    assert list(compute_features(_df()).columns) == FEATURE_COLUMNS


def test_features_are_causal_no_future_leakage():
    """A feature at time t must not change when future bars are added/removed."""
    df = _df(600)
    full = compute_features(df)
    trunc = compute_features(df.iloc[:450])
    a = full.iloc[:450].dropna()
    b = trunc.dropna()
    common = a.index.intersection(b.index)
    assert len(common) > 100                          # plenty of overlap to compare
    pd.testing.assert_frame_equal(a.loc[common], b.loc[common])
