"""Replay data handler — streams stored bars one timestamp at a time.

The lookahead-bias guarantee lives here: a cursor walks a master timeline, and
`get_latest_bars()` only ever returns rows at or before the cursor. There is no
public way to read a future bar mid-replay. The full frames are kept private so
the only path to data is the time-respecting API.
"""
from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional

import pandas as pd

from backtest.events import MarketEvent


class DataHandler:
    def __init__(self, bars: dict[str, pd.DataFrame], symbols: Optional[Iterable[str]] = None):
        """bars: {symbol -> OHLCV DataFrame indexed by tz-aware UTC timestamp}."""
        self.symbols = list(symbols) if symbols else list(bars)
        # private so strategies cannot peek ahead — the API below is the only door
        self._bars = {s: bars[s].sort_index() for s in self.symbols}
        union: set = set()
        for df in self._bars.values():
            union.update(df.index)
        self.timeline: list = sorted(union)
        self._i = -1                       # cursor; -1 = before the first bar
        self.continue_backtest = True

    @property
    def current_time(self) -> Optional[datetime]:
        if 0 <= self._i < len(self.timeline):
            return self.timeline[self._i]
        return None

    def update_bars(self) -> list[MarketEvent]:
        """Advance the cursor one step. Returns a MarketEvent, or [] when done."""
        self._i += 1
        if self._i >= len(self.timeline):
            self.continue_backtest = False
            return []
        return [MarketEvent(self.current_time)]

    def get_latest_bars(self, symbol: str, n: int = 1) -> pd.DataFrame:
        """The last `n` bars for `symbol` at or before the cursor (never future)."""
        now = self.current_time
        if now is None:
            return self._bars[symbol].iloc[:0]
        visible = self._bars[symbol].loc[self._bars[symbol].index <= now]
        return visible.tail(n)

    def get_latest_bar_value(self, symbol: str, field: str = "close") -> Optional[float]:
        bars = self.get_latest_bars(symbol, 1)
        if bars.empty or field not in bars.columns:
            return None
        return float(bars.iloc[-1][field])
