"""AlphaForge backend — FastAPI application entrypoint.

Wires together: health checks, market data REST, the live market WebSocket
(off the shared MarketSimulator), auth, and the trading/AI routers.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import psycopg2
import redis
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.config import settings
from api.market_sim import SIM
from api.routes import router
from auth.routes import router as auth_router
from data.storage import query_bars
from trading.routes import router as trading_router

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("alphaforge")

TICK_INTERVAL = 0.4  # seconds between simulator ticks / WS pushes


async def _ticker() -> None:
    i = 0
    while True:
        await asyncio.sleep(TICK_INTERVAL)
        SIM.tick()
        i += 1
        if i % 3 == 0:                       # ~1.2s: fill resting limit orders
            try:
                from trading.engine import sweep_open_limit_orders

                await asyncio.to_thread(sweep_open_limit_orders)
            except Exception as exc:  # noqa: BLE001 - DB may be down in dev
                logger.debug("limit sweep skipped: %s", exc)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Ensure the schema exists (idempotent) — lets a fresh managed Postgres
    # bootstrap itself on first deploy. Non-fatal if the DB isn't reachable.
    try:
        from data.storage import init_schema

        init_schema()
        logger.info("database schema ready")
    except Exception as exc:  # noqa: BLE001
        logger.warning("skipped schema init (db not ready?): %s", exc)

    task = asyncio.create_task(_ticker())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    title="AlphaForge",
    description="Systematic Trading & Research Platform — backend API.",
    version="0.2.0",
    lifespan=lifespan,
)

# Wide-open CORS for local dev; tighten before any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from ai.routes import router as ai_router  # noqa: E402 (after app deps ready)

app.include_router(router)
app.include_router(auth_router)
app.include_router(trading_router)
app.include_router(ai_router)


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
async def ws_market(ws: WebSocket, symbol: str = "RELIANCE") -> None:
    """Stream live price + depth snapshots (shared simulator) to the dashboard.

    The client may switch symbols mid-stream by sending {"symbol": "TCS"}.
    """
    await ws.accept()
    current = symbol.upper()
    try:
        while True:
            await asyncio.sleep(TICK_INTERVAL)
            # non-blocking check for a symbol-switch message
            with contextlib.suppress(asyncio.TimeoutError):
                text = await asyncio.wait_for(ws.receive_text(), timeout=0.001)
                import json as _json

                with contextlib.suppress(Exception):
                    requested = str(_json.loads(text).get("symbol", current)).upper()
                    if SIM.price(requested) is not None:
                        current = requested
            await ws.send_json(SIM.snapshot(current))
    except WebSocketDisconnect:
        return
    except Exception:  # noqa: BLE001 - client gone / send failed
        return


@app.get("/api/market/symbols")
def market_symbols() -> dict:
    """Tradable universe + latest prices (shared simulator)."""
    return {"symbols": SIM.symbols(), "prices": SIM.prices()}


# Serve the built React dashboard at "/" (single-origin deploy). Mounted LAST so
# /health, /api/*, /ws/*, /docs are matched first. Only active when the frontend
# has been built into ./static (the production Docker image does this); in local
# dev the Vite dev server / nginx handles the UI, so this stays inert.
_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if _STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="frontend")
