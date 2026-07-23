"""Phase 4 — the ML forecasting pipeline, end to end.

  load a Nifty universe
  -> monthly cross-sectional panel (features + forward-return rank target)
  -> walk-forward CV: out-of-sample predictions (LightGBM, sklearn fallback)
  -> Information Coefficient vs a momentum baseline
  -> SHAP feature attribution
  -> backtest the ML score as a dollar-neutral long/short strategy

    cd backend && python -m ml.run_ml
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from backtest.data import DataHandler
from backtest.engine import Backtest
from backtest.execution import SimulatedExecutionHandler
from backtest.performance import compute_metrics, format_metrics, turnover
from backtest.portfolio import Portfolio
from data.history import load_history
from ml.dataset import build_panel
from ml.evaluate import format_ic, ic_report, ic_series
from ml.features import FEATURE_COLUMNS
from ml.interpret import feature_importance, save_shap_summary
from ml.model import make_model, momentum_baseline, walk_forward_predict
from strategies.ml_strategy import MLStrategy

RESULTS = Path(__file__).resolve().parents[2] / "results"
UNIVERSE = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "ITC", "LT",
    "HINDUNILVR", "BHARTIARTL", "KOTAKBANK", "AXISBANK", "BAJFINANCE", "MARUTI",
    "ASIANPAINT", "HCLTECH", "WIPRO", "SUNPHARMA", "TITAN", "NTPC",
    "POWERGRID", "TATAMOTORS", "TATASTEEL", "ONGC",
]


def _load(symbols, start, end):
    bars = {}
    for s in symbols:
        df = load_history(s, start, end, "1d")
        if not df.empty:
            bars[s] = df
    return bars


def main(start="2015-01-01", end="2024-01-01") -> dict:
    bars = _load(UNIVERSE, start, end)
    print(f"loaded {len(bars)}/{len(UNIVERSE)} symbols")

    panel = build_panel(bars, horizon_months=1)
    print(f"panel: {len(panel)} rows | {panel['date'].nunique()} months | {panel['symbol'].nunique()} symbols")

    preds, model_name = walk_forward_predict(panel, min_train=36, test_size=12)
    base = momentum_baseline(panel, "ret_126")

    rep_model = ic_report(preds)
    rep_base = ic_report(base)
    print("\n=== out-of-sample Information Coefficient (walk-forward) ===")
    print(format_ic(model_name, rep_model))
    print(format_ic("momentum (ret_126)", rep_base))

    # LSTM sequence model — same folds, same IC metric (needs torch)
    from ml.lstm_model import torch_available, walk_forward_predict_lstm

    if torch_available():
        lstm_preds = walk_forward_predict_lstm(panel, window=6, min_train=36, test_size=12)
        print(format_ic("LSTM (seq)", ic_report(lstm_preds)))
    else:
        print("LSTM (seq)       skipped — pip install torch to enable")

    # interpretability — fit on the whole panel for a global attribution
    _, model = make_model()
    model.fit(panel[FEATURE_COLUMNS], panel["target"])
    imp = feature_importance(model, panel[FEATURE_COLUMNS])
    print("\n=== top features ===")
    print(imp.head(8).to_string())
    print("shap plot:", save_shap_summary(model, panel[FEATURE_COLUMNS]))

    # 4.7 — backtest the ML score as a dollar-neutral long/short book
    scores = preds.pivot_table(index="date", columns="symbol", values="pred")
    symbols = list(bars)
    data = DataHandler(bars, symbols)
    pf = Portfolio(data, symbols, initial_capital=100_000.0)
    pf = Backtest(data, MLStrategy(data, symbols, scores, quantile=0.3), pf,
                  SimulatedExecutionHandler(data)).run()
    eq = pf.equity_curve()
    metrics = compute_metrics(eq)
    print("\n=== ML long/short strategy backtest ===")
    print(format_metrics(metrics))
    print(f"  turnover     : {turnover(pf.trades, eq):>14.1f}")
    print(f"  trades       : {len(pf.trades):>14d}")

    RESULTS.mkdir(exist_ok=True)
    ic_series(preds).to_csv(RESULTS / "ic_series.csv")
    preds.to_csv(RESULTS / "ml_predictions.csv", index=False)
    eq.to_csv(RESULTS / "ml_strategy_equity.csv")
    return {"model": model_name, "ic_model": rep_model, "ic_base": rep_base, "backtest": metrics}


if __name__ == "__main__":
    main()
