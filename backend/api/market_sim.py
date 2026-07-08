"""One shared market state for the whole app.

A singleton `MarketSimulator` random-walks a small NSE universe; a background
task (started in the FastAPI lifespan) ticks it a few times a second. Every
consumer — the dashboard WebSocket, the paper broker, the AI trader — reads the
SAME prices, so fills, P&L, and charts are consistent across users and panels.

Swapping in a real feed later = replace `tick()` with a Redis subscriber that
writes into `self.px`; every consumer downstream is unchanged.
"""
from __future__ import annotations

import math
import random
import threading
import time
from collections import deque

UNIVERSE: dict[str, float] = {
    "RELIANCE": 2900.0,
    "TCS": 3850.0,
    "INFY": 1500.0,
    "HDFCBANK": 1650.0,
    "ICICIBANK": 1100.0,
}


class MarketSimulator:
    def __init__(self, prices: dict[str, float] | None = None, seed: int = 7,
                 vol: float = 0.0009, history_len: int = 600):
        self.px: dict[str, float] = dict(prices or UNIVERSE)
        self.open_px: dict[str, float] = dict(self.px)          # session opens
        self.vol = vol
        self._rng = random.Random(seed)
        self._lock = threading.Lock()
        # rolling per-symbol price history (for indicators / AI features)
        self.history: dict[str, deque[float]] = {s: deque([p], maxlen=history_len)
                                                 for s, p in self.px.items()}

    # ---- evolution --------------------------------------------------------
    def tick(self) -> None:
        with self._lock:
            for sym in self.px:
                step = math.exp(self._rng.gauss(0.0, self.vol))
                self.px[sym] = max(1.0, self.px[sym] * step)
                self.history[sym].append(self.px[sym])

    # ---- reads ------------------------------------------------------------
    def symbols(self) -> list[str]:
        return list(self.px)

    def price(self, symbol: str) -> float | None:
        return self.px.get(symbol.upper())

    def prices(self) -> dict[str, float]:
        with self._lock:
            return {s: round(p, 2) for s, p in self.px.items()}

    def series(self, symbol: str, n: int = 300) -> list[float]:
        h = self.history.get(symbol.upper())
        return list(h)[-n:] if h else []

    def depth(self, symbol: str, levels: int = 8) -> tuple[list, list]:
        """Synthetic order-book depth around the current price."""
        p = self.price(symbol)
        if p is None:
            return [], []
        bids = [[round(p * (1 - 0.0003 * (i + 1)), 2), self._rng.randint(50, 800)]
                for i in range(levels)]
        asks = [[round(p * (1 + 0.0003 * (i + 1)), 2), self._rng.randint(50, 800)]
                for i in range(levels)]
        return bids, asks

    def snapshot(self, symbol: str) -> dict:
        """The dashboard WebSocket message (same shape as before + all prices)."""
        sym = symbol.upper()
        bids, asks = self.depth(sym)
        p = self.price(sym) or 0.0
        o = self.open_px.get(sym, p) or p
        return {
            "type": "update",
            "ts": int(time.time()),
            "symbol": sym,
            "price": round(p, 2),
            "change_pct": round((p / o - 1.0) * 100, 3) if o else 0.0,
            "bids": bids,
            "asks": asks,
            "prices": self.prices(),
        }


# The app-wide singleton.
SIM = MarketSimulator()
