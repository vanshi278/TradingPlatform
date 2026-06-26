"""Common normalized market-data types shared across all sources and sinks.

Every feed source (broker WebSocket, synthetic, replay) emits `Tick`s in this
one format, so the rest of the system never has to care where data came from.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"
    UNKNOWN = "unknown"


def to_utc(ts: datetime) -> datetime:
    """Coerce a datetime to tz-aware UTC. Naive datetimes are assumed UTC."""
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class Tick:
    """A single normalized trade/quote print."""

    time: datetime           # tz-aware UTC
    symbol: str
    price: float
    size: float | None = None
    side: Side = Side.UNKNOWN
    source: str = "unknown"

    def to_dict(self) -> dict:
        return {
            "time": to_utc(self.time).isoformat(),
            "symbol": self.symbol,
            "price": self.price,
            "size": self.size,
            "side": self.side.value,
            "source": self.source,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, d: dict) -> "Tick":
        return cls(
            time=to_utc(datetime.fromisoformat(d["time"])),
            symbol=d["symbol"],
            price=float(d["price"]),
            size=None if d.get("size") is None else float(d["size"]),
            side=Side(d.get("side", "unknown")),
            source=d.get("source", "unknown"),
        )

    @classmethod
    def from_json(cls, s: str) -> "Tick":
        return cls.from_dict(json.loads(s))


@dataclass(frozen=True, slots=True)
class Bar:
    """A single OHLCV bar for a given interval."""

    time: datetime           # tz-aware UTC (bar open time)
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    interval: str = "1d"

    def to_dict(self) -> dict:
        return {
            "time": to_utc(self.time).isoformat(),
            "symbol": self.symbol,
            "interval": self.interval,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }
