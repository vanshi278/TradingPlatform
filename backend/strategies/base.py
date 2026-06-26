"""Base class every alpha strategy inherits.

A strategy reads bars from the DataHandler (only what it's allowed to see) and
returns SignalEvents. It never touches cash, sizing, or orders — that's the
portfolio's job — so strategies stay small and comparable.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from backtest.data import DataHandler
from backtest.events import MarketEvent, SignalEvent


class Strategy(ABC):
    def __init__(self, data: DataHandler, symbols: Iterable[str]):
        self.data = data
        self.symbols = list(symbols)

    @abstractmethod
    def calculate_signals(self, event: MarketEvent) -> list[SignalEvent]:
        """Return zero or more SignalEvents for the current bar."""
        raise NotImplementedError
