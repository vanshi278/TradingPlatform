"""AlphaForge backend — FastAPI application entrypoint.

Phase 0 scope: a runnable skeleton exposing health checks that verify
connectivity to TimescaleDB and Redis. The data, backtest, strategy,
execution, risk, and ML routers plug in here in later phases.
"""
from __future__ import annotations

import logging

import psycopg2
import redis
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.routes import router
from api.streaming import market_messages
from data.storage import query_bars

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("alphaforge")

app = FastAPI(
    title="AlphaForge",
    description="Systematic Trading & Research Platform — backend API.",
    version="0.1.0",
)

# Wide-open CORS for local dev; tighten before any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


def _check_postgres() -> bool:
    try:
        conn = psycopg2.connect(settings.pg_dsn, connect_timeout=2)
        conn.close()
        return True
    except Exception as exc:  # noqa: BLE001 - health check should never raise
        logger.warning("Postgres health check failed: %s", exc)
        return False


def _check_redis() -> bool:
    try:
        client = redis.from_url(settings.redis_url, socket_connect_timeout=2)
        return bool(client.ping())
    except Exception as exc:  # noqa: BLE001 - health check should never raise
        logger.warning("Redis health check failed: %s", exc)
        return False


@app.get("/")
def root() -> dict:
    return {
        "name": "AlphaForge",
        "tagline": "Systematic Trading & Research Platform",
        "version": app.version,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health() -> dict:
    pg_ok = _check_postgres()
    redis_ok = _check_redis()
    return {
        "status": "ok" if (pg_ok and redis_ok) else "degraded",
        "services": {
            "timescaledb": "up" if pg_ok else "down",
            "redis": "up" if redis_ok else "down",
        },
    }


@app.get("/data/bars")
def get_bars(
    symbol: str,
    interval: str = "1d",
    limit: int = Query(100, ge=1, le=5000),
) -> dict:
    """Most recent stored bars for a symbol (ascending). Reads TimescaleDB."""
    try:
        df = query_bars(symbol, interval=interval, limit=limit)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"TimescaleDB unavailable: {exc}")
    records = []
    if not df.empty:
        df = df.reset_index()
        df["time"] = df["time"].astype(str)
        records = df.to_dict("records")
    return {"symbol": symbol.upper(), "interval": interval, "count": len(records), "bars": records}


@app.websocket("/ws/market")
async def ws_market(ws: WebSocket) -> None:
    """Stream live price + order-book depth snapshots to the dashboard."""
    await ws.accept()
    try:
        async for msg in market_messages():
            await ws.send_json(msg)
    except WebSocketDisconnect:
        return
    except Exception:  # noqa: BLE001 - client gone / send failed
        return
