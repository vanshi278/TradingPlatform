# Data Layer (Pillar 1 · Phase 1)

Ingest real-time and historical market data concurrently from multiple sources
and store it as time series.

## What's here

| File | Role |
|------|------|
| `models.py` | Normalized `Tick` / `Bar` types (JSON-serializable) — the one format every source emits |
| `history.py` | `load_history(symbol, start, end, interval)` → clean UTC OHLCV via yfinance (NSE `.NS` mapping, split/dividend-adjusted) |
| `storage.py` | TimescaleDB I/O: `insert_bars` (idempotent upsert), `insert_ticks`, `query_bars`, `query_ticks`, `init_schema` |
| `bus.py` | Redis pub/sub: publish ticks to `ticks:<SYMBOL>`, async `subscribe()` for any number of independent consumers |
| `sources/` | `FeedSource` interface + `SyntheticFeedSource`, `ReplayFeedSource`, and a `KiteFeedSource` broker-WebSocket scaffold |
| `run_feeds.py` | Runs N sources concurrently → normalize → Redis, with a TimescaleDB writer subscriber |

## Try it

```bash
# Historical loader (real data, no keys, no Docker):
cd backend && python -m data.history --symbol RELIANCE --start 2022-01-01 --end 2024-01-01

# Concurrent multi-source feed, zero infrastructure:
cd backend && python -m data.run_feeds --no-redis --seconds 8

# Full pipeline (needs Docker: Redis + TimescaleDB) — publishers -> Redis ->
# two independent subscribers (console printer + DB writer):
docker compose up -d timescaledb redis
cd backend && python -m data.run_feeds --seconds 15
```

## Live broker feed

`sources/kite.py` is a scaffold: a real Zerodha Kite WebSocket bridged into the
same `FeedSource` async-generator interface. It needs `pip install kiteconnect`
and `KITE_API_KEY` / `KITE_ACCESS_TOKEN` in `.env`. Until then the synthetic and
replay sources stand in, so the entire pipeline runs without credentials or
market hours.

## Status

- [x] Historical loader — daily (2+ yrs) and intraday, 5+ symbols, UTC-normalized
- [x] TimescaleDB schema + read/write helpers (`db/init.sql` hypertables)
- [x] Redis pub/sub bus
- [x] Concurrent multi-source ingestion, one normalized tick format
- [~] Live broker WebSocket — interface + scaffold ready; activate with API keys
