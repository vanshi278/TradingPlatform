"""Limit order book + matching engine (Phase 5.1 / 5.2).

Price-time priority. Bids and asks live in `SortedDict`s (price -> Level); each
Level holds a `deque` of resting orders in arrival order; `order_map` gives O(1)
cancels via lazy tombstoning (a cancelled order is skipped at match time, and its
size is removed from the level immediately so depth/best stay exact).

A market order walks the opposite side level by level, so a large order fills at
progressively worse prices — visible price impact.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from itertools import count
from typing import Optional

from sortedcontainers import SortedDict


@dataclass
class Order:
    id: int
    side: str          # "buy" | "sell"
    price: float
    qty: int
    active: bool = True


@dataclass
class Fill:
    price: float
    qty: int
    aggressor_side: str
    resting_id: int


class _Level:
    __slots__ = ("queue", "qty")

    def __init__(self):
        self.queue: deque[Order] = deque()
        self.qty: int = 0


class LimitOrderBook:
    def __init__(self):
        self.bids: SortedDict = SortedDict()   # ascending; best bid = last key
        self.asks: SortedDict = SortedDict()   # ascending; best ask = first key
        self.order_map: dict[int, Order] = {}
        self._ids = count(1)

    # ---- top of book ----------------------------------------------------
    def best_bid(self) -> Optional[float]:
        return self.bids.peekitem(-1)[0] if self.bids else None

    def best_ask(self) -> Optional[float]:
        return self.asks.peekitem(0)[0] if self.asks else None

    def mid(self) -> Optional[float]:
        bb, ba = self.best_bid(), self.best_ask()
        return (bb + ba) / 2 if bb is not None and ba is not None else None

    def spread(self) -> Optional[float]:
        bb, ba = self.best_bid(), self.best_ask()
        return (ba - bb) if bb is not None and ba is not None else None

    def depth(self, side: str, n: int = 5) -> list[tuple[float, int]]:
        book = self.bids if side == "buy" else self.asks
        items = reversed(book.items()) if side == "buy" else book.items()
        out = []
        for price, lvl in items:
            if lvl.qty > 0:
                out.append((price, lvl.qty))
                if len(out) >= n:
                    break
        return out

    # ---- mutation -------------------------------------------------------
    def _book(self, side: str) -> SortedDict:
        return self.bids if side == "buy" else self.asks

    def add_limit(self, side: str, price: float, qty: int) -> tuple[int, list[Fill]]:
        """Add a limit order; marketable portion matches immediately, the rest rests."""
        fills: list[Fill] = []
        remaining = qty
        if side == "buy":
            while remaining > 0 and self.asks and self.best_ask() <= price:
                remaining, f = self._consume_best(self.asks, "buy", remaining)
                fills += f
        else:
            while remaining > 0 and self.bids and self.best_bid() >= price:
                remaining, f = self._consume_best(self.bids, "sell", remaining)
                fills += f

        oid = next(self._ids)
        if remaining > 0:
            book = self._book(side)
            lvl = book.get(price)
            if lvl is None:
                lvl = _Level()
                book[price] = lvl
            order = Order(oid, side, price, remaining)
            lvl.queue.append(order)
            lvl.qty += remaining
            self.order_map[oid] = order
        return oid, fills

    def market_order(self, side: str, qty: int) -> list[Fill]:
        """Walk the opposite side, filling level by level (price impact)."""
        opposite = self.asks if side == "buy" else self.bids
        fills: list[Fill] = []
        remaining = qty
        while remaining > 0 and opposite:
            remaining, f = self._consume_best(opposite, side, remaining)
            fills += f
        return fills

    def cancel(self, order_id: int) -> bool:
        order = self.order_map.pop(order_id, None)
        if order is None or not order.active:
            return False
        order.active = False                       # tombstone; skipped at match time
        book = self._book(order.side)
        lvl = book.get(order.price)
        if lvl is not None:
            lvl.qty -= order.qty
            if lvl.qty <= 0:
                del book[order.price]
        return True

    # ---- internal -------------------------------------------------------
    def _consume_best(self, book: SortedDict, aggressor_side: str, remaining: int):
        price, lvl = book.peekitem(0 if book is self.asks else -1)
        fills: list[Fill] = []
        while remaining > 0 and lvl.queue:
            order = lvl.queue[0]
            if not order.active:
                lvl.queue.popleft()
                continue
            take = min(remaining, order.qty)
            order.qty -= take
            lvl.qty -= take
            remaining -= take
            fills.append(Fill(price, take, aggressor_side, order.id))
            if order.qty == 0:
                order.active = False
                lvl.queue.popleft()
                self.order_map.pop(order.id, None)
        if lvl.qty <= 0 or not lvl.queue:
            del book[price]
        return remaining, fills
