"""Live market message stream for the dashboard WebSocket.

Emits a price + order-book-depth snapshot a few times a second. Uses the
synthetic feed so the dashboard is live with zero infrastructure (no Docker, no
broker keys, no market hours). Swap in a Redis subscriber here for real ticks.
"""
from __future__ import annotations

import asyncio
import math
import random
import time
from typing import AsyncIterator


async def market_messages(
    symbol: str = "RELIANCE",
    price0: float = 2900.0,
    interval: float = 0.4,
    seed: int = 7,
) -> AsyncIterator[dict]:
    rng = random.Random(seed)
    price = price0
    while True:
        await asyncio.sleep(interval)
        price = max(1.0, price * math.exp(rng.gauss(0.0, 0.0009)))
        bids = [[round(price * (1 - 0.0003 * (i + 1)), 2), rng.randint(50, 800)] for i in range(8)]
        asks = [[round(price * (1 + 0.0003 * (i + 1)), 2), rng.randint(50, 800)] for i in range(8)]
        yield {
            "type": "update",
            "ts": int(time.time()),
            "symbol": symbol,
            "price": round(price, 2),
            "bids": bids,
            "asks": asks,
        }
