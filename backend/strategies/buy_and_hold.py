"""Buy & hold — buy each symbol on its first available bar, then never trade.
A plumbing sanity check: its equity curve should track the underlying."""
from __future__ import annotations

from backtest.events import MarketEvent, SignalEvent
from strategies.base import Strategy


class BuyAndHold(Strategy):
    def __init__(self, data, symbols):
        super().__init__(data, symbols)
        self._bought = {s: False for s in self.symbols}

    def calculate_signals(self, event: MarketEvent) -> list[SignalEvent]:
        signals = []
        for sym in self.symbols:
            if not self._bought[sym] and self.data.get_latest_bar_value(sym, "close") is not None:
                signals.append(SignalEvent(sym, event.time, "LONG"))
                self._bought[sym] = True
        return signals
