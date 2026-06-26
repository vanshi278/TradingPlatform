"""Orders fill at the NEXT bar's open, with slippage and commission applied."""
import pytest

from backtest.data import DataHandler
from backtest.events import OrderEvent
from backtest.execution import SimulatedExecutionHandler


def test_fills_at_next_bar_open(make_bars):
    # distinct opens so we can tell which bar was used to fill
    bars = make_bars(closes=[100, 110], opens=[100, 108])
    data = DataHandler({"TEST": bars}, ["TEST"])
    execn = SimulatedExecutionHandler(data, slippage_bps=10.0, commission_bps=5.0)

    data.update_bars()                       # cursor -> bar 0
    execn.on_order(OrderEvent("TEST", "MKT", 10, "BUY"))  # queued during bar 0

    data.update_bars()                       # cursor -> bar 1
    fills = execn.fill_pending()             # fills at bar 1's open
    assert len(fills) == 1
    f = fills[0]
    # filled at bar 1's open (108), not bar 0's open (100)
    expected_price = 108 * (1 + 10 / 1e4)    # buy slips up
    assert f.fill_price == pytest.approx(expected_price)
    assert f.commission == pytest.approx(5 / 1e4 * expected_price * 10)
    assert f.direction == "BUY" and f.quantity == 10


def test_sell_slips_down(make_bars):
    bars = make_bars(closes=[100, 100], opens=[100, 100])
    data = DataHandler({"TEST": bars}, ["TEST"])
    execn = SimulatedExecutionHandler(data, slippage_bps=20.0, commission_bps=0.0)

    data.update_bars()
    execn.on_order(OrderEvent("TEST", "MKT", 5, "SELL"))
    data.update_bars()
    f = execn.fill_pending()[0]
    assert f.fill_price == pytest.approx(100 * (1 - 20 / 1e4))   # sell slips down
