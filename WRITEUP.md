# AlphaForge — design notes & results

A walk through the decisions behind the platform and the numbers it produces. The
theme throughout: **measure honestly**. Modest, correctly-measured alpha and
realistic execution cost are worth more than an inflated backtest.

---

## 1. Why event-driven (and how lookahead bias is killed)

A vectorized backtester computes signals over an entire price series at once — fast,
but it's far too easy to let information from the future leak into a past decision. An
**event-driven** loop instead processes one timestamp at a time through a single queue
(`MarketEvent → SignalEvent → OrderEvent → FillEvent`), which mirrors how a live system
actually runs and makes leakage structurally hard.

Two independent guards enforce no-lookahead:

1. **Data cursor.** The `DataHandler` keeps the full price frames *private* and exposes
   only `get_latest_bars()`, which filters to timestamps `≤ now`. There is no public way
   to read a future bar mid-replay. A test (`test_no_lookahead.py`) runs a probe strategy
   over a full replay and asserts it never observes a timestamp beyond "now", and that
   exactly one new bar becomes visible per step.
2. **Deferred fills.** An order decided on bar *t* is filled at bar *t+1*'s **open**, never
   at the close the strategy just used to decide. The execution handler holds the order and
   fills it when the next bar arrives.

> Interview answer to "how did you avoid lookahead bias?": the strategy can only ever see
> `≤ now` through the data API, and orders fill at the next bar's open — so a decision can
> never use a price it couldn't have traded on.

---

## 2. Almgren-Chriss optimal execution (the headline result)

Executing a large order has two opposing costs: trade **fast** and you pay market impact
(walking the order book); trade **slow** and you're exposed to price drift (timing risk).
Almgren-Chriss makes that trade-off explicit with a risk-aversion `λ` and a closed-form
holdings trajectory:

```
x_j = X · sinh(κ (T − t_j)) / sinh(κ T),   κ = sqrt(λ σ² / η̃)
```

`λ → 0` gives a straight line (uniform / TWAP-like); large `λ` front-loads the schedule.

We execute TWAP, VWAP, and AC schedules against the **simulated limit order book** (market
orders walk price levels at worsening prices) over many Monte-Carlo paths and measure
implementation shortfall:

| Schedule | Mean IS (bps) | Std IS / risk (bps) |
|----------|--------------:|--------------------:|
| TWAP | 6.9 | 27.0 |
| AC (high λ) | 9.3 | **19.5** |

**Almgren-Chriss cut timing risk ~28% (27.0 → 19.5 bps) for +2.4 bps of mean impact.**
That's the efficient-frontier point: front-loading spends a little more on impact to spend
much less time exposed to drift.

One subtlety worth stating: in the **linear** AC model, *permanent* impact is
schedule-independent (a fixed cost), so it doesn't change the optimal trajectory — we set it
to zero in the comparison to isolate the temporary-impact-vs-risk trade-off rather than
inflate every number equally.

---

## 3. The ML signal — rigor over model

The goal is a *useful, honest* predictive signal, not a high-accuracy headline.

- **Target = cross-sectional rank of forward return**, not raw price. Predicting absolute
  price is a red flag; what matters for a long/short book is *relative* ordering.
- **Walk-forward cross-validation.** Train on past months, test on the next unseen block,
  roll forward. A test month is never in training. Time is never shuffled.
- **Causal features.** All 22 features at time *t* use only data `≤ t`; a test proves that
  truncating the future doesn't change a past feature value.
- **Two models, same folds.** A LightGBM/sklearn tree model and an LSTM sequence model
  (PyTorch, consuming a window of monthly feature vectors) are evaluated on identical
  walk-forward folds with the same IC metric — an honest, apples-to-apples comparison.
- **Evaluate with Information Coefficient** (per-month rank correlation of prediction vs.
  realized return), not accuracy.

Result on a 24-name Nifty universe (2015–2024, monthly, strictly out-of-sample):

| Signal | Mean IC | IC IR | t-stat | Hit rate |
|--------|--------:|------:|-------:|---------:|
| Gradient-boosted trees | **+0.024** | 0.11 | 0.86 | 49% |
| LSTM sequence model | **+0.022** | 0.09 | 0.71 | 51% |
| Momentum baseline | −0.012 | −0.04 | −0.30 | 49% |

Both models beat the momentum baseline, but at ~0.02–0.03 on a 23-name universe the IC is
**modest and not statistically significant** (t < 2) — the honest read is "a small positive
edge, correctly measured," not a strong signal. That candor is the point: on a bigger
universe the signal would firm up. SHAP shows the top drivers (RSI, distance-from-52-week-low,
short-term reversal, volatility), so it isn't a black box.

> Note: the intended model is LightGBM; it falls back to scikit-learn's
> `GradientBoostingRegressor` on machines without `libomp`. The methodology is identical.

---

## 4. Risk engine

99% 1-day VaR / CVaR computed three ways on an equal-weight portfolio:

| Method | VaR | CVaR |
|--------|----:|-----:|
| Historical | $34,366 | $54,955 |
| Parametric | $28,269 | $32,517 |
| Monte-Carlo | $28,495 | $32,747 |

The three agree in ballpark, but **historical VaR runs higher** — real returns have fat
tails the Gaussian methods understate, which is exactly why you compute it more than one
way. A **Kupiec** backtest validates the model: 15 breaches vs 12.3 expected (p = 0.45),
not rejected. Pre-trade limits resize or block oversized orders, and a drawdown kill switch
flattens the book past a threshold.

---

## 5. Engineering choices

- **FastAPI (async)** — first-class WebSocket/async support for the live tick stream.
- **TimescaleDB** — time-series done properly (hypertables), not CSV dumps.
- **Redis pub/sub** — one tick stream that any number of consumers subscribe to.
- **Target-weight portfolio** — every strategy routes through one "rebalance to X% of
  equity" primitive, so long, short, scale, and flip are all the same code path (this is
  what made pairs and dollar-neutral long/short fall out cleanly).
- **NSE equities, not crypto** — local-market awareness, and it avoids the crowded
  crypto-bot space.

---

## 6. Honest limitations

- The **live** tick stream is a synthetic feed (no broker keys / market hours needed); a
  real Zerodha Kite WebSocket plugs into the same `FeedSource` interface.
- The bar backtester can't host a live order book per bar, so Phase 5's impact model is
  reused as a **square-root impact fill** rather than replaying a full book historically.
- Cross-sectional momentum was run on a small basket; real cross-sectional momentum needs a
  Nifty-500-scale universe.
- Daily bars; intraday is supported by the loader but not the focus.

---

## Run it

```bash
docker compose up -d          # TimescaleDB + Redis + backend + dashboard
# dashboard: http://localhost:3000   API docs: http://localhost:8000/docs

cd backend && pytest          # 70 tests
python -m execution.run_execution   # the Almgren-Chriss comparison
python -m ml.run_ml                 # the IC report
python -m risk.run_risk             # VaR / Kupiec / kill switch
```
