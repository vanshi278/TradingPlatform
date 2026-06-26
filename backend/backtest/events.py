"""The four event types that flow through the single backtest queue.

    MarketEvent  -> a new bar is available (the data handler is the source of truth)
    SignalEvent  -> a strategy wants to take/exit a position
    OrderEvent   -> the portfolio has sized that intent into an order
    FillEvent    -> the execution handler filled the order (with cost)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Optional


@dataclass
class MarketEvent:
    type: ClassVar[str] = "MARKET"
    time: datetime


@dataclass
class SignalEvent:
    type: ClassVar[str] = "SIGNAL"
    symbol: str
    time: datetime
    signal: str           # "LONG" | "EXIT" | "SHORT"
    strength: float = 1.0


@dataclass
class OrderEvent:
    type: ClassVar[str] = "ORDER"
    symbol: str
    order_type: str       # "MKT"
    quantity: int         # always positive; see `direction`
    direction: str        # "BUY" | "SELL"
    time: Optional[datetime] = None


@dataclass
class FillEvent:
    type: ClassVar[str] = "FILL"
    symbol: str
    time: datetime
    quantity: int
    direction: str        # "BUY" | "SELL"
    fill_price: float
    commission: float = 0.0

    @property
    def signed_quantity(self) -> int:
        return self.quantity if self.direction == "BUY" else -self.quantity
