# Résumé bullets — AlphaForge

Honest, quantified bullets drawn from the project. Trim/tailor per role (quant
vs. backend vs. full-stack). Repo: github.com/vanshi278/TradingPlatform

## One-line project header
**AlphaForge — Systematic Trading & Research Platform** · Python (FastAPI), React, TimescaleDB, Redis, Docker · [github.com/vanshi278/TradingPlatform](https://github.com/vanshi278/TradingPlatform)

## Bullets (pick 4–6)

- Built an **event-driven backtesting engine** with structural lookahead-bias
  protection (a private data cursor plus next-bar-open fills), proven by a test
  asserting no future data is ever visible mid-replay.

- Implemented **Almgren-Chriss optimal execution** against a custom
  limit-order-book simulator (price-time priority, O(1) cancels, Poisson order
  flow, Kyle-λ impact); **cut execution timing risk ~28% vs. TWAP** at +2.4 bps
  cost over 200 Monte-Carlo paths.

- Developed **ML alpha signals** — a LightGBM tree model **and an LSTM** (PyTorch)
  across **22 features** — using walk-forward cross-validation and cross-sectional
  rank targets; both beat a momentum baseline on out-of-sample **Information
  Coefficient** (~0.02–0.03, honestly reported on a 23-name universe), with SHAP
  interpretability.

- Engineered a **real-time risk engine**: 99% VaR/CVaR three ways (historical,
  parametric, Monte-Carlo), a Kupiec exception backtest, pre-trade exposure
  limits, and a drawdown kill switch.

- Shipped a **live trading platform**: JWT authentication, an order-management
  system (market/limit/cancel, positions & P&L derived from fills), risk-gated
  order placement, and an **AI auto-trader** (LLM + rule-based) that logs every
  decision's rationale; env-gated Angel One broker integration.

- Delivered a **React + lightweight-charts dashboard** streaming live prices and
  order-book depth over WebSocket, with an in-browser backtest runner and live
  risk panel.

- Backed by **90 automated tests** and one-command `docker compose up`
  (TimescaleDB + Redis + FastAPI + React), with continuous integration on
  GitHub Actions.

## Talking points (for interviews)
- Why event-driven over vectorized (execution realism + no lookahead).
- Why predict return *rank*, not price (cross-sectional signal, honest IC).
- The Almgren-Chriss cost-vs-risk trade-off and why permanent impact is
  schedule-independent in the linear model.
- How positions/P&L are *derived from fills* (single source of truth, no drift).
