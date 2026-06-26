"""Replay a historical OHLCV frame as a 'live' tick stream — each bar's close
becomes a tick. Deterministic, offline, and a natural bridge from the history
loader to the live pipeline (and later, the backtester).
"""
from __future__ import annotations

import asyncio
from typing import AsyncIterator, Optional

import pandas as pd

from data.models import Tick
from data.sources.base import FeedSource


class ReplayFeedSource(FeedSource):
    def __init__(
        self,
        df: pd.DataFrame,
        name: str = "replay",
        speed: float = 60.0,
        fixed_sleep: Optional[float] = None,
        max_sleep: float = 2.0,
    ):
        """df: a frame from load_history (UTC index, 'symbol' + 'close' columns).

        speed: wall-clock compression (60 = 1 simulated minute per real second).
        fixed_sleep: if set, sleep this many seconds between ticks instead.
        """
        self.df = df
        self.name = name
        self.speed = speed
        self.fixed_sleep = fixed_sleep
        self.max_sleep = max_sleep

    async def stream(self) -> AsyncIterator[Tick]:
        prev_ts = None
        for ts, row in self.df.iterrows():
            if self.fixed_sleep is not None:
                await asyncio.sleep(self.fixed_sleep)
            elif prev_ts is not None:
                dt = (ts - prev_ts).total_seconds() / max(self.speed, 1e-9)
                await asyncio.sleep(min(max(dt, 0.0), self.max_sleep))
            prev_ts = ts
            vol = row.get("volume")
            yield Tick(
                time=ts.to_pydatetime(),
                symbol=str(row["symbol"]),
                price=float(row["close"]),
                size=(float(vol) if vol is not None and not pd.isna(vol) else None),
                source=self.name,
            )
