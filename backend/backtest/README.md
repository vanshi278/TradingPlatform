# Backtest Engine (Pillar 2 · Phase 2)

An **event-driven** backtester (not vectorized) — it mirrors the real execution
loop and structurally prevents lookahead bias.

## What's here

| File | Role |
|------|------|
| `events.py` | `MarketEvent`, `SignalEvent`, `OrderEvent`, `FillEvent` |
| `data.py` | `DataHandler` — replays bars one timestamp at a time; `get_latest_bars()` can only ever see ≤ now |
| `execution.py` | `SimulatedExecutionHandler` — fills at the **next bar's open** + slippage + commission |
| `portfolio.py` | `Portfolio` — sizes signals into orders, applies fills, records per-bar equity |
| `performance.py` | total return, CAGR, annualized Sharpe, max drawdown |
| `engine.py` | `Backtest` — the single-queue event loop wiring it together |
| `run_backtest.py` | CLI: load data → run → metrics + equity CSV/PNG |

## How lookahead bias is prevented

Two independent guards:
1. **Data cursor** — the handler walks a master timeline; `get_latest_bars()`
   filters to timestamps `<= current_time`. The full frames are private, so
   there is no API to read a future bar.
2. **Deferred fills** — an order raised on bar *t* is held and filled at bar
   *t+1*'s open, never at the close the strategy just used to decide.

`tests/test_no_lookahead.py` asserts the strategy never observes a timestamp
beyond "now" across an entire replay.

## Run it

```bash
cd backend
python -m backtest.run_backtest --symbols RELIANCE --strategy buyhold --start 2018-01-01 --end 2024-01-01
python -m backtest.run_backtest --symbols RELIANCE --strategy ma --short 20 --long 50
```

## Status

- [x] Event types + single-queue loop (a MarketEvent flows through to a FillEvent)
- [x] Replay data handler with proven no-lookahead guarantee
- [x] Portfolio: sizing, fills, cash/positions, equity curve
- [x] Next-open execution with slippage + commission (Phase 5 swaps in the LOB sim)
- [x] Buy & hold + MA crossover strategies
- [x] Performance metrics + equity/drawdown plot
