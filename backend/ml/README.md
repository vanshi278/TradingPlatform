# ML / Forecasting Module (Pillar 4 · Phase 4)

A rigorous predictive signal. The methodology — no leakage, walk-forward, honest
out-of-sample IC — matters more than the model.

## What's here

| File | Role |
|------|------|
| `features.py` | 22 causal features (returns, vol, RSI, volume, trend, mean-reversion, range) |
| `lstm_model.py` | LSTM sequence model (PyTorch) evaluated on the same walk-forward folds |
| `dataset.py` | monthly cross-sectional panel; target = cross-sectional **rank** of forward 1-month return |
| `walkforward.py` | time-ordered walk-forward CV (train past → test next unseen block → roll) |
| `model.py` | LightGBM (sklearn `GradientBoostingRegressor` fallback) + momentum baseline |
| `evaluate.py` | Information Coefficient: per-month rank corr, mean IC, IC IR, t-stat, hit rate |
| `interpret.py` | SHAP feature attribution (falls back to `feature_importances_`) |
| `run_ml.py` | the full pipeline + ML long/short backtest (`strategies/ml_strategy.py`) |

## Why these choices (the interview answers)
- **Rank target, not raw price** — predicting absolute price is a red flag; we
  predict the cross-sectional ranking of next-month returns.
- **Walk-forward, never shuffle** — a test month is never in training; this is
  the main guard against an over-optimistic ML backtest.
- **Features are causal** — every feature at time t uses only data ≤ t
  (`tests/test_ml_features.py` proves truncating the future doesn't change them).
- **IC, honestly** — mean IC ≈ 0.02–0.06 is a genuinely useful equity signal.

## Result (24-name Nifty universe, 2015–2024, monthly)
- Gradient-boosted trees (sklearn-gbr*) OOS **mean IC ≈ +0.024**; LSTM (PyTorch) **≈ +0.022** — same folds, same metric.
- Momentum baseline (`ret_126`): **mean IC ≈ −0.012** — both models beat it.
- ML long/short backtest: +21.8% total, Sharpe 0.42, max drawdown only **−10.4%** (dollar-neutral).
- Honest caveat: on a 23-name universe the IC is modest and noisy (t < 2, not significant).

\* LightGBM is the intended model; it falls back to scikit-learn here because
macOS `libomp` isn't installed (`brew install libomp` activates LightGBM — the
code switches automatically).

## Run it
```bash
cd backend && python -m ml.run_ml
```

## Status
- [x] 4.1 Feature engineering (22 features, no NaN leakage)
- [x] 4.2 Target = cross-sectional forward-return rank
- [x] 4.3 Walk-forward cross-validation
- [x] 4.4 Baseline (momentum) + models (LightGBM/sklearn **and LSTM**) over the same folds
- [x] 4.5 Information Coefficient report
- [x] 4.6 SHAP interpretability
- [x] 4.7 ML score wired into a backtested long/short strategy
