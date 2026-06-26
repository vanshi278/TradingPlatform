"""Cash and positions update correctly across a buy then a sell."""
import pytest

from backtest.data import DataHandler
from backtest.events import FillEvent, SignalEvent
from backtest.portfolio import Portfolio

T = None  # filled per-test from the bar timestamp


def test_sizing_and_roundtrip_accounting(make_bars):
    data = DataHandler({"TEST": make_bars([100.0, 100.0, 100.0])}, ["TEST"])
    data.update_bars()                                   # cursor -> bar 0, close=100
    pf = Portfolio(data, ["TEST"], initial_capital=100_000.0, target_pct=0.95)
    t = data.current_time

    # LONG -> size at 95% of equity / price = 950 shares
    orders = pf.update_signal(SignalEvent("TEST", t, "LONG"))
    assert len(orders) == 1 and orders[0].direction == "BUY" and orders[0].quantity == 950

    # apply the buy fill (no commission) and check cash/positions
    pf.update_fill(FillEvent("TEST", t, 950, "BUY", 100.0, commission=0.0))
    assert pf.positions["TEST"] == 950
    assert pf.cash == pytest.approx(100_000 - 950 * 100)         # 5,000
    assert pf.total_equity() == pytest.approx(100_000)           # 5,000 cash + 95,000 holdings

    # a second LONG while already long does nothing
    assert pf.update_signal(SignalEvent("TEST", t, "LONG")) == []

    # EXIT -> sell the whole position
    orders = pf.update_signal(SignalEvent("TEST", t, "EXIT"))
    assert orders == [orders[0]] and orders[0].direction == "SELL" and orders[0].quantity == 950
    pf.update_fill(FillEvent("TEST", t, 950, "SELL", 100.0, commission=0.0))
    assert pf.positions["TEST"] == 0
    assert pf.cash == pytest.approx(100_000)
    assert len(pf.trades) == 2


def test_commission_reduces_cash(make_bars):
    data = DataHandler({"TEST": make_bars([100.0])}, ["TEST"])
    data.update_bars()
    pf = Portfolio(data, ["TEST"], initial_capital=10_000.0)
    pf.update_fill(FillEvent("TEST", data.current_time, 10, "BUY", 100.0, commission=7.5))
    assert pf.cash == pytest.approx(10_000 - 1000 - 7.5)
