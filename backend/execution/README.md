# Execution Engine + LOB Simulator (Pillar 5 · Phase 5)

Realistic order execution against a simulated limit order book — Milestone 3, the
headline quant result.

## What's here

| File | Role |
|------|------|
| `order_book.py` | `LimitOrderBook` — `SortedDict` bids/asks, `deque` per level, O(1) cancels; market orders walk levels at worsening prices |
| `flow.py` | `OrderFlowGenerator` — Poisson inter-arrivals, limit/market/cancel, log-normal sizes |
| `impact.py` | `LinearImpactModel` — Kyle-λ permanent + decaying temporary impact |
| `almgren_chriss.py` | closed-form `sinh` trajectory (risk-aversion λ) |
| `schedules.py` | TWAP, VWAP (volume profile), Almgren-Chriss schedules |
| `simulator.py` | execute a schedule vs the LOB; implementation shortfall + Monte-Carlo |
| `run_execution.py` | the TWAP vs VWAP vs AC comparison demo |

## The headline result

```bash
cd backend && python -m execution.run_execution
```

Buying 50,000 shares over 20 slices, 200 Monte-Carlo paths:

| Schedule | Mean IS (bps) | Std IS / risk (bps) |
|----------|--------------:|--------------------:|
| TWAP | 6.9 | 27.0 |
| VWAP (U-shape) | 7.0 | 26.2 |
| AC (low λ) | 6.9 | 26.7 |
| AC (high λ) | 9.3 | **19.5** |

**Almgren-Chriss (high λ) cut timing risk ~28% (27.0 → 19.5 bps) for +2.4 bps of
mean impact** — the classic cost-vs-risk trade-off. Front-loading reduces the
time the order is exposed to price drift, at the cost of walking deeper into the
book early. (Permanent impact is set to zero here because in the linear model it
is schedule-independent, so it doesn't affect the trade-off.)

## Status
- [x] 5.1 Limit order book (add/cancel/best-bid/ask, tested)
- [x] 5.2 Matching engine (market order walks levels at worsening prices)
- [x] 5.3 Poisson order-flow generator (churning book)
- [x] 5.4 Linear price-impact model (permanent + decaying temporary)
- [x] 5.5 Almgren-Chriss `sinh` trajectory (λ→0 uniform, λ large front-loaded)
- [x] 5.6 TWAP & VWAP baselines
- [x] 5.7 All schedules executed through the LOB
- [x] 5.8 Implementation-shortfall comparison (bps) + plots
- [x] 5.9 Swapped into the backtester (`ImpactExecutionHandler`, `run_backtest --execution impact`)
