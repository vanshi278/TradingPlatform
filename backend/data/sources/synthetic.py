"""Synthetic random-walk feed — a credential-free stand-in for a live broker
WebSocket. Lets you build and demo the whole pipeline off-hours and without API
keys. Inter-arrival times are exponential (Poisson process); prices take small
Gaussian steps.
"""
from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone
from typing import AsyncIterator, Optional

from data.models import Side, Tick
from data.sources.base import FeedSource


class SyntheticFeedSource(FeedSource):
    def __init__(
        self,
        prices: dict[str, float],
        rate_per_sec: float = 2.0,
        name: str = "synthetic",
        vol_bps: float = 5.0,
        seed: Optional[int] = None,
        max_ticks: Optional[int] = None,
    ):
        self.prices = dict(prices)
        self.rate = rate_per_sec
        self.name = name
        self.vol_bps = vol_bps
        self.max_ticks = max_ticks
        self._rng = random.Random(seed)

    async def stream(self) -> AsyncIterator[Tick]:
        symbols = list(self.prices)
        emitted = 0
        while self.max_ticks is None or emitted < self.max_ticks:
            await asyncio.sleep(self._rng.expovariate(self.rate))
            sym = self._rng.choice(symbols)
            px = self.prices[sym]
            px = max(0.01, px + self._rng.gauss(0.0, self.vol_bps / 1e4) * px)
            self.prices[sym] = px
            emitted += 1
            yield Tick(
                time=datetime.now(timezone.utc),
                symbol=sym,
                price=round(px, 2),
                size=float(self._rng.randint(1, 500)),
                side=self._rng.choice([Side.BUY, Side.SELL]),
                source=self.name,
            )
