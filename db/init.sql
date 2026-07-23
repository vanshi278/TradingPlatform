-- AlphaForge — TimescaleDB schema.
-- Runs automatically on first container start via /docker-entrypoint-initdb.d.
-- This is the foundation the Phase 1 data layer writes to and reads from.

-- TimescaleDB is used for the hypertables when available (local Docker image).
-- On a plain managed Postgres (Render/Railway/Neon) the extension isn't present,
-- so we degrade gracefully to ordinary tables — the app works either way.
DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS timescaledb;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'TimescaleDB unavailable — using plain Postgres tables';
END $$;

-- ---------------------------------------------------------------------------
-- Raw trade / quote ticks (the live feed lands here).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ticks (
    time   TIMESTAMPTZ      NOT NULL,
    symbol TEXT             NOT NULL,
    price  DOUBLE PRECISION NOT NULL,
    size   DOUBLE PRECISION,
    side   TEXT
);
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'create_hypertable') THEN
        PERFORM create_hypertable('ticks', 'time', if_not_exists => TRUE);
    END IF;
END $$;
CREATE INDEX IF NOT EXISTS idx_ticks_symbol_time ON ticks (symbol, time DESC);

-- ---------------------------------------------------------------------------
-- OHLCV bars (any interval; the interval is kept as a column so daily and
-- intraday bars share one hypertable).
-- ---------------------------------------------------------------------------
-- ---------------------------------------------------------------------------
-- Users (auth) — signup/login with bcrypt-hashed passwords.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    email           TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Order management system: orders + fills (positions are derived from fills).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS orders (
    id          TEXT PRIMARY KEY,                  -- uuid4 string
    user_id     INTEGER NOT NULL REFERENCES users(id),
    symbol      TEXT NOT NULL,
    side        TEXT NOT NULL,                     -- buy | sell
    order_type  TEXT NOT NULL,                     -- market | limit
    qty         INTEGER NOT NULL,
    limit_price DOUBLE PRECISION,
    status      TEXT NOT NULL,                     -- open|filled|cancelled|rejected|resized
    reason      TEXT,                              -- risk-gate note / AI rationale
    source      TEXT NOT NULL DEFAULT 'manual',    -- manual | ai
    mode        TEXT NOT NULL DEFAULT 'paper',     -- paper | live
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_orders_user_time ON orders (user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS fills (
    id         SERIAL PRIMARY KEY,
    order_id   TEXT NOT NULL REFERENCES orders(id),
    user_id    INTEGER NOT NULL REFERENCES users(id),
    symbol     TEXT NOT NULL,
    side       TEXT NOT NULL,
    qty        INTEGER NOT NULL,
    price      DOUBLE PRECISION NOT NULL,
    commission DOUBLE PRECISION NOT NULL DEFAULT 0,
    time       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_fills_user_time ON fills (user_id, time DESC);

-- ---------------------------------------------------------------------------
-- AI trader decision log — every signal, with rationale, even when no order.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ai_decisions (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    time       TIMESTAMPTZ NOT NULL DEFAULT now(),
    symbol     TEXT NOT NULL,
    action     TEXT NOT NULL,                      -- buy | sell | hold
    confidence DOUBLE PRECISION,
    rationale  TEXT,
    order_id   TEXT,                               -- set when an order was placed
    features   JSONB
);
CREATE INDEX IF NOT EXISTS idx_ai_decisions_user_time ON ai_decisions (user_id, time DESC);

CREATE TABLE IF NOT EXISTS bars (
    time     TIMESTAMPTZ      NOT NULL,
    symbol   TEXT             NOT NULL,
    interval TEXT             NOT NULL DEFAULT '1d',
    open     DOUBLE PRECISION,
    high     DOUBLE PRECISION,
    low      DOUBLE PRECISION,
    close    DOUBLE PRECISION,
    volume   DOUBLE PRECISION,
    PRIMARY KEY (symbol, interval, time)
);
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'create_hypertable') THEN
        PERFORM create_hypertable('bars', 'time', if_not_exists => TRUE);
    END IF;
END $$;
CREATE INDEX IF NOT EXISTS idx_bars_symbol_interval_time ON bars (symbol, interval, time DESC);
