"""The headline guarantee: a strategy can never see a future bar mid-replay."""
from backtest.data import DataHandler
from backtest.engine import Backtest
from backtest.execution import SimulatedExecutionHandler
from backtest.portfolio import Portfolio
from strategies.base import Strategy


class _Probe(Strategy):
    """Records, on every bar, the newest timestamp it can see vs. 'now'."""

    def __init__(self, data, symbols):
        super().__init__(data, symbols)
        self.violations = []
        self.visible_counts = []

    def calculate_signals(self, event):
        for sym in self.symbols:
            bars = self.data.get_latest_bars(sym, 10_000)
            if bars.empty:
                continue
            newest = bars.index.max()
            self.visible_counts.append(len(bars))
            if newest > event.time:
                self.violations.append((event.time, newest))
        return []


def test_strategy_never_sees_the_future(make_bars):
    closes = list(range(100, 130))  # 30 strictly increasing bars
    data = DataHandler({"TEST": make_bars(closes)}, ["TEST"])
    probe = _Probe(data, ["TEST"])
    Backtest(data, probe, Portfolio(data, ["TEST"]), SimulatedExecutionHandler(data)).run()

    assert probe.violations == []                 # never peeked ahead
    # exactly one more bar becomes visible each step: 1, 2, 3, ... , N
    assert probe.visible_counts == list(range(1, len(closes) + 1))


def test_get_latest_bars_tracks_cursor(make_bars):
    data = DataHandler({"TEST": make_bars(list(range(10)))}, ["TEST"])
    seen = 0
    while True:
        evs = data.update_bars()
        if not evs:
            break
        seen += 1
        bars = data.get_latest_bars("TEST", 10_000)
        assert bars.index.max() == data.current_time   # newest visible == now
        assert len(bars) == seen                        # nothing from the future
