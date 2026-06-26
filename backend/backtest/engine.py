"""The event-driven backtest loop.

One queue, four event types. Each bar:
  1. data.update_bars()            -> MarketEvent(t) onto the queue
  2. drain the queue:
       MARKET -> execution.fill_pending() fills last bar's orders at t's open
                 (FillEvents); strategy.calculate_signals() -> SignalEvents
       SIGNAL -> portfolio.update_signal() -> OrderEvents
       ORDER  -> execution.on_order() (held; fills next bar)
       FILL   -> portfolio.update_fill() (cash + positions)
  3. portfolio.update_timeindex(t) -> record equity at the bar's close

Because orders raised on bar t are only filled when bar t+1 arrives, the
strategy can never trade on information it could not have had. Combined with the
data handler's cursor, that is the lookahead-bias protection.
"""
from __future__ import annotations

from queue import Empty, Queue

from backtest.data import DataHandler
from backtest.events import FillEvent, MarketEvent, OrderEvent, SignalEvent
from backtest.execution import SimulatedExecutionHandler
from backtest.portfolio import Portfolio


class Backtest:
    def __init__(
        self,
        data: DataHandler,
        strategy,
        portfolio: Portfolio,
        execution: SimulatedExecutionHandler,
    ):
        self.data = data
        self.strategy = strategy
        self.portfolio = portfolio
        self.execution = execution
        self.queue: "Queue" = Queue()
        self.counts = {"MARKET": 0, "SIGNAL": 0, "ORDER": 0, "FILL": 0}

    def _dispatch(self, event) -> None:
        self.counts[event.type] += 1
        if event.type == MarketEvent.type:
            for fill in self.execution.fill_pending():
                self.queue.put(fill)
            for signal in self.strategy.calculate_signals(event):
                self.queue.put(signal)
        elif event.type == SignalEvent.type:
            for order in self.portfolio.update_signal(event):
                self.queue.put(order)
        elif event.type == OrderEvent.type:
            self.execution.on_order(event)
        elif event.type == FillEvent.type:
            self.portfolio.update_fill(event)

    def run(self) -> Portfolio:
        while self.data.continue_backtest:
            market_events = self.data.update_bars()
            if not market_events:
                break
            for ev in market_events:
                self.queue.put(ev)
            # drain every event this bar generates before closing the bar out
            while True:
                try:
                    event = self.queue.get_nowait()
                except Empty:
                    break
                self._dispatch(event)
            self.portfolio.update_timeindex(self.data.current_time)
        return self.portfolio
