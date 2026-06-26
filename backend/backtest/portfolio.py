"""Portfolio / position tracker.

Turns SignalEvents into sized OrderEvents, applies FillEvents to cash and
positions, and records a per-bar equity time series (marked at each bar's
close). Long/flat only in Phase 2 (shorting arrives with the richer strategies).
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from backtest.data import DataHandler
from backtest.events import FillEvent, OrderEvent, SignalEvent


class Portfolio:
    def __init__(
        self,
        data: DataHandler,
        symbols,
        initial_capital: float = 100_000.0,
        target_pct: float = 0.95,
    ):
        self.data = data
        self.symbols = list(symbols)
        self.initial_capital = float(initial_capital)
        self.target_pct = target_pct

        self.cash = float(initial_capital)
        self.positions: dict[str, int] = {s: 0 for s in self.symbols}
        self.history: list[dict] = []     # per-bar equity snapshots
        self.trades: list[FillEvent] = []

    # ---- valuation -------------------------------------------------------
    def holdings_value(self) -> float:
        total = 0.0
        for sym, qty in self.positions.items():
            if qty == 0:
                continue
            px = self.data.get_latest_bar_value(sym, "close")
            if px is not None:
                total += qty * px
        return total

    def total_equity(self) -> float:
        return self.cash + self.holdings_value()

    # ---- event handlers --------------------------------------------------
    def update_signal(self, signal: SignalEvent) -> list[OrderEvent]:
        sym = signal.symbol
        price = self.data.get_latest_bar_value(sym, "close")
        if price is None or price <= 0:
            return []
        pos = self.positions[sym]

        if signal.signal == "LONG":
            if pos > 0:
                return []                       # already long
            qty = int((self.target_pct * self.total_equity()) // price)
            return [OrderEvent(sym, "MKT", qty, "BUY", signal.time)] if qty > 0 else []

        if signal.signal in ("EXIT", "SHORT"):
            # Phase 2 is long/flat: any exit/short intent just flattens the book
            if pos > 0:
                return [OrderEvent(sym, "MKT", pos, "SELL", signal.time)]
            return []

        return []

    def update_fill(self, fill: FillEvent) -> None:
        notional = fill.quantity * fill.fill_price
        if fill.direction == "BUY":
            self.cash -= notional + fill.commission
        else:
            self.cash += notional - fill.commission
        self.positions[fill.symbol] += fill.signed_quantity
        self.trades.append(fill)

    def update_timeindex(self, time) -> None:
        self.history.append(
            {
                "time": time,
                "cash": self.cash,
                "holdings": self.holdings_value(),
                "total": self.total_equity(),
            }
        )

    # ---- output ----------------------------------------------------------
    def equity_curve(self) -> pd.DataFrame:
        if not self.history:
            return pd.DataFrame(columns=["cash", "holdings", "total", "returns", "equity"])
        df = pd.DataFrame(self.history).set_index("time")
        df["returns"] = df["total"].pct_change().fillna(0.0)
        df["equity"] = df["total"] / self.initial_capital
        return df
