"""Simulated execution — the Phase 2 placeholder fill model.

Orders are filled at the NEXT bar's open (plus slippage and commission), never
at the close the strategy just used to decide. Mechanically this is enforced by
deferring fills: an order received during bar t is held and filled when bar t+1
arrives, at t+1's open. Phase 5 replaces this with the limit-order-book sim.
"""
from __future__ import annotations

from backtest.data import DataHandler
from backtest.events import FillEvent, OrderEvent


class SimulatedExecutionHandler:
    def __init__(
        self,
        data: DataHandler,
        slippage_bps: float = 1.0,
        commission_bps: float = 1.0,
        min_commission: float = 0.0,
    ):
        self.data = data
        self.slippage_bps = slippage_bps
        self.commission_bps = commission_bps
        self.min_commission = min_commission
        self._pending: list[OrderEvent] = []

    def on_order(self, order: OrderEvent) -> None:
        """Queue an order; it fills on the next bar (see fill_pending)."""
        self._pending.append(order)

    def fill_pending(self) -> list[FillEvent]:
        """Fill all queued orders at the CURRENT bar's open (= next bar relative
        to when each order was created). Called at the top of each new bar."""
        if not self._pending:
            return []
        fills: list[FillEvent] = []
        slip = self.slippage_bps / 1e4
        for order in self._pending:
            open_px = self.data.get_latest_bar_value(order.symbol, "open")
            if open_px is None:
                continue  # no bar to fill against; drop
            # slippage always works against the trader
            price = open_px * (1 + slip) if order.direction == "BUY" else open_px * (1 - slip)
            commission = max(self.min_commission, self.commission_bps / 1e4 * price * order.quantity)
            fills.append(
                FillEvent(
                    symbol=order.symbol,
                    time=self.data.current_time,
                    quantity=order.quantity,
                    direction=order.direction,
                    fill_price=price,
                    commission=commission,
                )
            )
        self._pending = []
        return fills
