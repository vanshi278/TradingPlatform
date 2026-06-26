"""Zerodha Kite live feed (broker WebSocket) — scaffold.

Requires `pip install kiteconnect` and valid credentials (KITE_API_KEY,
KITE_ACCESS_TOKEN). Until those exist, SyntheticFeedSource / ReplayFeedSource
stand in. The whole point of this class is that a *real* broker feed plugs into
the exact same FeedSource interface the pipeline already consumes — bridging the
KiteTicker callback world into our async generator via a thread-safe queue.

`kiteconnect` is imported lazily so the package imports fine without it.
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import AsyncIterator, Optional

from data.models import Tick
from data.sources.base import FeedSource


class KiteFeedSource(FeedSource):
    name = "kite"

    def __init__(
        self,
        symbol_token_map: dict[str, int],
        api_key: Optional[str] = None,
        access_token: Optional[str] = None,
    ):
        self.symbol_token_map = symbol_token_map
        self.token_symbol = {tok: sym for sym, tok in symbol_token_map.items()}
        self.api_key = api_key or os.getenv("KITE_API_KEY")
        self.access_token = access_token or os.getenv("KITE_ACCESS_TOKEN")

    async def stream(self) -> AsyncIterator[Tick]:
        if not (self.api_key and self.access_token):
            raise RuntimeError(
                "KiteFeedSource needs KITE_API_KEY and KITE_ACCESS_TOKEN (set them "
                "in .env). For a credential-free demo use SyntheticFeedSource or "
                "ReplayFeedSource."
            )
        try:
            from kiteconnect import KiteTicker
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("pip install kiteconnect to use the live Kite feed") from exc

        queue: asyncio.Queue[Tick] = asyncio.Queue()
        loop = asyncio.get_running_loop()
        tokens = list(self.token_symbol)
        kws = KiteTicker(self.api_key, self.access_token)

        def on_ticks(ws, ticks):  # runs on KiteTicker's own thread
            for t in ticks:
                sym = self.token_symbol.get(t.get("instrument_token"), str(t.get("instrument_token")))
                tick = Tick(
                    time=datetime.now(timezone.utc),
                    symbol=sym,
                    price=float(t.get("last_price", 0.0)),
                    size=t.get("last_traded_quantity"),
                    source=self.name,
                )
                loop.call_soon_threadsafe(queue.put_nowait, tick)

        def on_connect(ws, response):
            ws.subscribe(tokens)
            ws.set_mode(ws.MODE_FULL, tokens)

        kws.on_ticks = on_ticks
        kws.on_connect = on_connect
        kws.connect(threaded=True)
        try:
            while True:
                yield await queue.get()
        finally:  # pragma: no cover
            kws.close()
