import numpy as np
import pandas as pd

from ml.evaluate import ic_report


def _preds(transform, periods=4, names=12, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for d in range(periods):
        fwd = rng.normal(0, 1, names)
        for i in range(names):
            rows.append({"date": d, "symbol": i, "pred": transform(fwd[i]), "fwd_ret": fwd[i]})
    return pd.DataFrame(rows)


def test_perfect_alignment_gives_ic_near_one():
    rep = ic_report(_preds(lambda x: x))
    assert rep["mean_ic"] > 0.99
    assert rep["n_periods"] == 4
    assert rep["hit_rate"] == 1.0


def test_reversed_alignment_gives_negative_ic():
    rep = ic_report(_preds(lambda x: -x))
    assert rep["mean_ic"] < -0.99
