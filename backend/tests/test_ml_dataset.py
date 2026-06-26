import numpy as np
import pandas as pd

from ml.dataset import build_panel
from ml.features import FEATURE_COLUMNS


def _bars(symbol, n=500, seed=0):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.012, n)))
    idx = pd.date_range("2018-01-01", periods=n, freq="D", tz="UTC")
    return pd.DataFrame(
        {"open": close, "high": close * 1.01, "low": close * 0.99,
         "close": close, "volume": 1e6, "symbol": symbol},
        index=idx,
    )


def test_panel_has_features_target_and_no_feature_nans():
    bars = {f"S{i}": _bars(f"S{i}", seed=i) for i in range(6)}
    panel = build_panel(bars, horizon_months=1)

    assert not panel.empty
    assert set(FEATURE_COLUMNS).issubset(panel.columns)
    assert {"target", "fwd_ret", "symbol", "date"}.issubset(panel.columns)
    assert panel[FEATURE_COLUMNS].isna().sum().sum() == 0     # no leakage via NaN fill
    assert panel["target"].between(-0.5, 0.5).all()            # centered rank target
