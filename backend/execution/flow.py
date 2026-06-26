"""Poisson order-flow generator (Phase 5.3).

Exponential inter-arrival times; each event is a limit / market / cancel order
with configurable probabilities; sizes are log-normal; limit prices sit a random
number of ticks from mid. Running it churns a realistic book.
"""
from __future__ import annotations

import numpy as np

from execution.order_book import LimitOrderBook


class OrderFlowGenerator:
    def __init__(
        self,
        rate: float = 10.0,
        p_market: float = 0.2,
        p_cancel: float = 0.3,
        tick: float = 0.05,
        mean_size: int = 100,
        sigma_size: float = 0.5,
        depth_ticks: int = 10,
        seed=None,
    ):
        self.rate = rate
        self.p_market = p_market
        self.p_cancel = p_cancel
        self.tick = tick
        self.mean_size = mean_size
        self.sigma_size = sigma_size
        self.depth_ticks = depth_ticks
        self.rng = np.random.default_rng(seed)
        self.clock = 0.0

    def _size(self) -> int:
        return max(1, int(self.rng.lognormal(np.log(self.mean_size), self.sigma_size)))

    def seed_book(self, book: LimitOrderBook, mid: float, levels: int = 10, per_level: int = 300) -> None:
        """Lay down symmetric resting liquidity around `mid`."""
        for i in range(1, levels + 1):
            book.add_limit("buy", round(mid - i * self.tick, 4), per_level)
            book.add_limit("sell", round(mid + i * self.tick, 4), per_level)

    def step(self, book: LimitOrderBook) -> float:
        """Apply one random event. Returns the (exponential) time since the last."""
        dt = float(self.rng.exponential(1.0 / self.rate))
        self.clock += dt
        mid = book.mid()
        if mid is None:
            return dt
        u = self.rng.random()
        ids = list(book.order_map.keys())
        if u < self.p_cancel and ids:
            book.cancel(int(self.rng.choice(ids)))
        elif u < self.p_cancel + self.p_market:
            side = "buy" if self.rng.random() < 0.5 else "sell"
            book.market_order(side, self._size())
        else:
            side = "buy" if self.rng.random() < 0.5 else "sell"
            offset = (1 + int(self.rng.integers(0, self.depth_ticks))) * self.tick
            price = round(mid - offset, 4) if side == "buy" else round(mid + offset, 4)
            book.add_limit(side, price, self._size())
        return dt

    def run(self, book: LimitOrderBook, n_events: int) -> LimitOrderBook:
        for _ in range(n_events):
            self.step(book)
        return book
