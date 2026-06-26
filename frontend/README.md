# React Dashboard (Pillar 7 · Phase 7)

The cockpit — React + Vite + Tailwind + TradingView's
[`lightweight-charts`](https://github.com/tradingview/lightweight-charts).

## What's here

| Component | Panel |
|-----------|-------|
| `PriceChart.jsx` | live candlestick (WS ticks aggregated into 2s candles) |
| `OrderBook.jsx` | order-book depth ladder (live WS snapshot) |
| `BacktestForm.jsx` | pick strategy / symbols / dates / execution → run |
| `EquityPanel.jsx` | equity curve from the backtest result |
| `PositionsTable.jsx` | open positions |
| `RiskPanel.jsx` | 99% VaR (hist + parametric), max drawdown, kill-switch status |

The live price + order book stream from the backend WebSocket (`/ws/market`,
fed by the synthetic feed — no Docker, no broker keys). The lower panels are
driven by `POST /api/backtest/run`, which runs the real Phase 2–6 engine.

## Run it

```bash
# 1. backend (serves /ws/market and /api/*)
cd backend && uvicorn api.main:app --port 8000

# 2. dashboard (Vite dev server proxies /api and /ws to :8000)
cd frontend && npm install && npm run dev      # http://localhost:5173
```

## Status
- [x] 7.1 Vite + React + Tailwind + lightweight-charts scaffold
- [x] 7.2 WebSocket from backend (live ticks to the browser)
- [x] 7.3 Live candlestick + order-book depth ladder
- [x] 7.4 P&L: equity curve + positions table
- [x] 7.5 Backtest runner UI (form → run → metrics + equity)
- [x] 7.6 Risk panel (live VaR, drawdown, kill-switch status)
