"""Redis pub/sub bus for the live tick stream.

Publishers (feed sources) push normalized Ticks as JSON onto per-symbol
channels `ticks:<SYMBOL>`. Any number of independent subscribers (DB writer,
frontend gateway, strategies) consume the same stream without coupling.
"""
from __future__ import annotations

import contextlib
from typing import AsyncIterator, Iterable, Optional

import redis.asyncio as aioredis

from api.config import settings
from data.models import Tick

CHANNEL_PREFIX = "ticks:"


def channel_for(symbol: str) -> str:
    return f"{CHANNEL_PREFIX}{symbol.upper()}"


def get_redis() -> "aioredis.Redis":
    """A fresh async Redis client (decoded to str)."""
    return aioredis.from_url(settings.redis_url, decode_responses=True)


async def close_redis(r) -> None:
    with contextlib.suppress(Exception):
        await r.aclose()


async def publish_tick(r, tick: Tick) -> None:
    await r.publish(channel_for(tick.symbol), tick.to_json())


async def subscribe(r, symbols: Optional[Iterable[str]] = None) -> AsyncIterator[Tick]:
    """Yield Ticks for the given symbols, or all symbols (pattern) if None."""
    pubsub = r.pubsub()
    if symbols:
        await pubsub.subscribe(*[channel_for(s) for s in symbols])
    else:
        await pubsub.psubscribe(f"{CHANNEL_PREFIX}*")
    try:
        async for msg in pubsub.listen():
            if msg.get("type") in ("message", "pmessage"):
                yield Tick.from_json(msg["data"])
    finally:
        with contextlib.suppress(Exception):
            await pubsub.aclose()
