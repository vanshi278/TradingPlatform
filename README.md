# AlphaForge — Systematic Trading & Research Platform

> A mini version of what a quant desk runs internally: **data in → research & signals in the middle → execution & risk out.** Built on Indian equities (NSE / Nifty), not crypto.

**Status:** 🚧 Work in progress, built in vertical slices.
- **✅ Phase 0 — Foundations:** repo skeleton, Dockerized TimescaleDB + Redis, runnable FastAPI with live health checks.
- **✅ Phase 1 — Data Layer:** historical loader (NSE equities via yfinance), TimescaleDB read/write, Redis pub/sub bus, and 3 concurrent feeds normalized into one tick format. Live broker WebSocket scaffolded (activate with API keys).
- **✅ Phase 2 — Event-Driven Backtester:** single-queue event loop with **proven lookahead-bias protection**, next-open fills (slippage + commission), portfolio accounting, buy & hold + MA-crossover strategies, and equity-curve metrics (Sharpe, CAGR, max drawdown).
- **✅ Phase 3 — Alpha / Strategy module:** short-selling + target-weight rebalancing, pairs trading on cointegrated spreads (Engle-Granger), cross-sectional long/short momentum, an inventory-managed market-making sim, and a strategy comparison report.
- **✅ Phase 4 — ML / Forecasting:** causal feature engineering, a forward-return **rank** target, **walk-forward** cross-validation, LightGBM (sklearn fallback) vs a momentum baseline, an honest **Information Coefficient** report (mean IC ≈ +0.047 out-of-sample), SHAP attribution, and the ML score backtested as a dollar-neutral long/short.

---

## What it is

AlphaForge ingests real-time and historical market data, researches and generates
trading signals, simulates **realistic** order execution against a limit-order-book,
and runs a **live risk engine** — all surfaced through a React dashboard. It is
designed as a portfolio-grade demonstration of the full systematic-trading stack,
with an emphasis on the things quants actually care about: no lookahead bias,
honest out-of-sample evaluation, and realistic execution cost.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       REACT DASHBOARD                        │
│   live charts · order book · P&L · risk panel · backtest UI  │
└───────────────────────────┬─────────────────────────────────┘
                            │ WebSocket / REST
┌───────────────────────────┴─────────────────────────────────┐
│                  FASTAPI BACKEND (async)                     │
├──────────┬───────────┬────────────┬───────────┬─────────────┤
│  DATA    │ BACKTEST  │   ALPHA    │ EXECUTION │    RISK      │
│  LAYER   │  ENGINE   │  + ML      │  ENGINE   │   ENGINE     │
└──────────┴───────────┴────────────┴───────────┴─────────────┘
       │                                              │
┌──────┴──────────┐                        ┌──────────┴────────┐
│  TimescaleDB +  │                        │  Live broker API  │
│     Redis       │                        │  or paper-trading │
└─────────────────┘                        └───────────────────┘
```

## The 7 pillars

| # | Pillar | What it does | Phase |
|---|--------|--------------|-------|
| 1 | **Data Layer** | Concurrent real-time + historical ingestion → TimescaleDB, Redis pub/sub bus | 1 |
| 2 | **Backtest Engine** | Event-driven loop with structural lookahead-bias protection | 2 |
| 3 | **Alpha / Strategy** | Pluggable strategies: mean reversion, momentum, market making | 3 |
| 4 | **ML / Forecasting** | Forward-return rank prediction, walk-forward CV, IC, SHAP | 4 |
| 5 | **Execution Engine** | LOB simulator + Almgren-Chriss vs TWAP/VWAP, implementation shortfall | 5 |
| 6 | **Risk Engine** | Live VaR/CVaR, exposure limits, drawdown kill switch | 6 |
| 7 | **React Dashboard** | Live charts, depth ladder, P&L, risk panel, backtest runner | 7 |

## Tech decisions

| Layer | Choice | Why |
|-------|--------|-----|
| **Asset class** | NSE equities (Nifty) | Signals local-market awareness; differentiates from crypto-bot resumes |
| **Backend** | FastAPI (async) | First-class async/WebSocket support for real-time data; what newer quant shops use |
| **Database** | TimescaleDB (Postgres) | Time-series done properly — what real shops use, not CSV dumps |
| **Cache / bus** | Redis pub/sub | One live tick stream that strategy + frontend + DB writer all subscribe to |
| **Backtest** | Event-driven (not vectorized) | Mirrors the real execution loop; structurally avoids lookahead bias |
| **ML target** | Forward-return rank / direction | Raw price prediction is a red flag; evaluate with IC + walk-forward CV |
| **Execution** | LOB sim + Almgren-Chriss + TWAP/VWAP | Realistic slippage and price impact, measured in BPS |
| **Frontend** | React + Vite + Tailwind + lightweight-charts | Industry-standard, fast charts (TradingView, free) |
| **Deploy** | Docker Compose | One-command spin-up |

## Project structure

```
AI_TRADING_PLATFORM/
├── backend/
│   ├── api/            # FastAPI app (REST + WebSocket)  ← runnable now
│   ├── data/           # ingestion + storage            ← built (Phase 1)
│   ├── backtest/       # event-driven engine            (Phase 2)
│   ├── strategies/     # pluggable alpha                (Phase 3)
│   ├── ml/             # forecasting models             (Phase 4)
│   ├── execution/      # LOB sim + Almgren-Chriss        (Phase 5)
│   ├── risk/           # VaR / limits / kill switch     (Phase 6)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/           # React dashboard                (Phase 7)
├── notebooks/          # research / EDA / reports
├── db/
│   └── init.sql        # TimescaleDB hypertables (ticks, bars)
├── docker-compose.yml
├── .env.example
└── README.md
```

## Getting started

### Prerequisites
- **Docker Desktop** (with Docker Compose v2+) — for TimescaleDB, Redis, and the backend.
- **Python 3.11+** — only if you want to run/develop the backend outside Docker.

### 1. Clone
```bash
git clone https://github.com/vanshi278/alphaforge.git
cd alphaforge
```

### 2. Spin up the stack (one command)
```bash
docker compose up -d
```
This starts:
- **TimescaleDB** on `localhost:5432` (hypertables `ticks` and `bars` created automatically from [`db/init.sql`](db/init.sql))
- **Redis** on `localhost:6379`
- **Backend API** on `localhost:8000`

Verify it's healthy:
```bash
curl http://localhost:8000/health
# {"status":"ok","services":{"timescaledb":"up","redis":"up"}}
```
Interactive API docs (Swagger UI): **http://localhost:8000/docs**

> Just the data services, without the backend container:
> `docker compose up -d timescaledb redis`

### 3. Backend dev environment (optional — for local hacking)
```bash
cp .env.example .env          # POSTGRES_HOST/REDIS_URL already default to localhost
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# run the API against the Dockerized DB + Redis
cd backend && uvicorn api.main:app --reload
```

## Data layer (Phase 1)

```bash
# Historical OHLCV — real NSE data, no keys, no Docker:
cd backend && python -m data.history --symbol RELIANCE --start 2022-01-01 --end 2024-01-01

# Concurrent multi-source live feed, zero infrastructure (3 normalized feeds):
cd backend && python -m data.run_feeds --no-redis --seconds 8

# Full pipeline (Docker up): publishers → Redis → two independent subscribers
# (a console printer and a TimescaleDB writer):
docker compose up -d timescaledb redis
cd backend && python -m data.run_feeds --seconds 15

# Query stored bars through the API:
curl "http://localhost:8000/data/bars?symbol=RELIANCE&interval=1d&limit=5"
```

Run the tests (DB tests auto-skip if TimescaleDB isn't up):
```bash
cd backend && pytest
```

See [backend/data/README.md](backend/data/README.md) for the full data-layer map.
A real Zerodha Kite WebSocket feed plugs into the same interface once you add
`KITE_API_KEY` / `KITE_ACCESS_TOKEN` to `.env`.

## Backtesting (Phase 2)

```bash
cd backend
python -m backtest.run_backtest --symbols RELIANCE --strategy buyhold --start 2018-01-01 --end 2024-01-01
python -m backtest.run_backtest --symbols RELIANCE --strategy ma --short 20 --long 50 --start 2018-01-01 --end 2024-01-01
```

Sample run on RELIANCE (2018–2024, daily, next-open fills, 1 bps slippage + commission):

| Strategy | Total return | CAGR | Sharpe | Max drawdown | Trades |
|----------|-------------:|-----:|-------:|-------------:|-------:|
| Buy & hold | 207.5% | 21.1% | 0.81 | −43.8% | 1 |
| MA 20/50 crossover | 53.8% | 7.6% | 0.49 | −42.0% | 39 |

The crossover *underperforming* buy & hold through a strong bull market is the
honest, expected result — trend filters cost you in trending-up regimes. The
point of the engine is to measure that truthfully (no lookahead, realistic
fills), not to manufacture a flattering number. See
[backend/backtest/README.md](backend/backtest/README.md) for how lookahead bias
is structurally prevented.

## Strategy comparison (Phase 3)

```bash
cd backend && python -m backtest.compare
```

All strategies run through the same engine over 2018–2024 (each on its natural
universe), ranked on return / risk / turnover:

| Strategy | Total return | CAGR | Sharpe | Max drawdown | Turnover | Trades |
|----------|-------------:|-----:|-------:|-------------:|---------:|-------:|
| Buy & hold (RELIANCE) | 207.5% | 21.1% | 0.81 | −43.8% | 0.5 | 1 |
| MA 20/50 (RELIANCE) | 53.8% | 7.6% | 0.49 | −42.0% | 37.7 | 39 |
| Pairs TCS/INFY | 12.8% | 2.1% | 0.35 | **−18.2%** | 71.2 | 140 |
| X-sec momentum (8-name basket) | −21.6% | −4.1% | −0.27 | −34.7% | 48.3 | 319 |

Honest readout: buy & hold wins the bull market outright; the market-neutral
**pairs** book has by far the shallowest drawdown (−18% vs −44%), which is the
point of a hedged strategy; and naive cross-sectional momentum on an 8-name
basket *loses* — real cross-sectional momentum needs a Nifty-500-scale universe,
not eight names. The framework's job is to surface that truthfully.

## ML signal (Phase 4)

```bash
cd backend && python -m ml.run_ml
```

Cross-sectional forward-return forecasting on a 24-name Nifty universe (2015–2024,
monthly), evaluated strictly out-of-sample with walk-forward CV:

| Signal | Mean IC | IC IR | t-stat | Hit rate |
|--------|--------:|------:|-------:|---------:|
| ML model (gradient-boosted trees) | **+0.047** | 0.22 | 1.66 | 61% |
| Momentum baseline (`ret_126`) | −0.012 | −0.04 | −0.30 | 49% |

The ML score, backtested as a dollar-neutral long/short, returned +19.9% with a
max drawdown of just −12.5%. A mean IC of ~0.047 is a genuinely useful (and
honest) equity signal — the rigor is in *how* it's measured: a **rank** target
(not raw price), strictly causal features (`tests/test_ml_features.py` proves
no future leakage), walk-forward folds that never train on a test month, and
SHAP attribution so the model isn't a black box. See
[backend/ml/README.md](backend/ml/README.md).

## Build roadmap (progress)

- [x] **Phase 0 — Setup & Foundations** · repo skeleton, env, Docker (TimescaleDB + Redis), runnable FastAPI health check
- [x] **Phase 1 — Data Layer** · historical loader (yfinance/NSE), TimescaleDB I/O, Redis pub/sub bus, 3 concurrent normalized feeds · *live broker WebSocket scaffolded, pending API keys*
- [x] **Phase 2 — Event-Driven Backtester** · single-queue loop, no-lookahead replay handler, next-open fills, portfolio, buy&hold + MA strategies, equity-curve metrics
- [x] **Phase 3 — Alpha / Strategy** · pairs/cointegration, cross-sectional momentum, market making, short-selling, comparison report
- [x] **Phase 4 — ML / Forecasting** · causal features, rank target, walk-forward CV, LightGBM/sklearn vs momentum, IC report, SHAP, ML long/short
- [ ] **Phase 5 — Execution + LOB** · order book, matching engine, Almgren-Chriss, TWAP/VWAP, implementation shortfall
- [ ] **Phase 6 — Risk Engine** · VaR/CVaR, Kupiec test, limits, drawdown kill switch
- [ ] **Phase 7 — React Dashboard** · live charts, depth ladder, P&L, backtest runner, risk panel
- [ ] **Phase 8 — Polish** · results-led README, one-command spin-up, tests, write-up

## Disclaimer

Educational / research project. **Not investment advice.** No warranty; use at your own risk.
