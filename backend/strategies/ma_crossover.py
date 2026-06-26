"""Moving-average crossover — go long when the short SMA is above the long SMA,
flat otherwise. The classic trend-following sanity strategy."""
from __future__ import annotations

from backtest.events import MarketEvent, SignalEvent
from strategies.base import Strategy


class MACrossover(Strategy):
    def __init__(self, data, symbols, short_window: int = 20, long_window: int = 50):
        super().__init__(data, symbols)
        if short_window >= long_window:
            raise ValueError("short_window must be < long_window")
        self.short_window = short_window
        self.long_window = long_window
        self._in_market = {s: False for s in self.symbols}

    def calculate_signals(self, event: MarketEvent) -> list[SignalEvent]:
        signals = []
        for sym in self.symbols:
            bars = self.data.get_latest_bars(sym, self.long_window)
            if len(bars) < self.long_window:
                continue
            closes = bars["close"]
            short_ma = closes.tail(self.short_window).mean()
            long_ma = closes.mean()  # exactly long_window bars
            if short_ma > long_ma and not self._in_market[sym]:
                signals.append(SignalEvent(sym, event.time, "LONG"))
                self._in_market[sym] = True
            elif short_ma < long_ma and self._in_market[sym]:
                signals.append(SignalEvent(sym, event.time, "EXIT"))
                self._in_market[sym] = False
        return signals
