import numpy as np
import pandas as pd

from backtest.data import DataHandler
from backtest.engine import Backtest
from backtest.execution import SimulatedExecutionHandler
from backtest.portfolio import Portfolio
from strategies.ml_strategy import MLStrategy


def _bars(symbol, n=120, start="2020-01-01"):
    closes = 100 * np.exp(np.cumsum(np.full(n, 0.001)))
    idx = pd.date_range(start, periods=n, freq="D", tz="UTC")
    return pd.DataFrame(
        {"open": closes, "high": closes, "low": closes, "close": closes,
         "volume": 1000.0, "symbol": symbol},
        index=idx,
    )


def test_ml_strategy_longs_high_scores_shorts_low():
    syms = ["A", "B", "C", "D"]
    bars = {s: _bars(s) for s in syms}
    data = DataHandler(bars, syms)
    scores = pd.DataFrame(
        {"A": [0.4], "B": [0.1], "C": [-0.1], "D": [-0.4]},
        index=[pd.Timestamp("2020-02-15", tz="UTC")],
    )
    pf = Portfolio(data, syms, initial_capital=100_000.0)
    pf = Backtest(data, MLStrategy(data, syms, scores, quantile=0.3), pf,
                  SimulatedExecutionHandler(data)).run()

    assert pf.positions["A"] > 0      # top score -> long
    assert pf.positions["D"] < 0      # bottom score -> short
