"""End-to-end: MarketEvents flow through the queue and produce a FillEvent,
and the portfolio ends invested with a full-length equity curve."""
from backtest.data import DataHandler
from backtest.engine import Backtest
from backtest.execution import SimulatedExecutionHandler
from backtest.portfolio import Portfolio
from strategies import BuyAndHold


def test_full_event_chain(make_bars):
    closes = [100, 101, 102, 103, 104]
    data = DataHandler({"TEST": make_bars(closes)}, ["TEST"])
    pf = Portfolio(data, ["TEST"], initial_capital=100_000.0)
    bt = Backtest(data, BuyAndHold(data, ["TEST"]), pf, SimulatedExecutionHandler(data))
    pf = bt.run()

    # every event type fired -> the loop really is end-to-end
    assert bt.counts["MARKET"] == len(closes)
    assert bt.counts["SIGNAL"] >= 1
    assert bt.counts["ORDER"] >= 1
    assert bt.counts["FILL"] >= 1

    # buy & hold: one fill, ends long, equity recorded once per bar
    assert len(pf.trades) == 1 and pf.trades[0].direction == "BUY"
    assert pf.positions["TEST"] > 0
    assert len(pf.equity_curve()) == len(closes)

    # signal raised on bar 0 fills on bar 1 (next open), never bar 0
    assert pf.trades[0].time == data.timeline[1]
