"""Phase 5.9 — the impact-aware backtest fill handler charges more for larger
orders (square-root market impact)."""
from backtest.data import DataHandler
from backtest.events import OrderEvent
from backtest.execution import ImpactExecutionHandler


def _fill_for_qty(make_bars, qty):
    bars = make_bars(closes=[100.0, 100.0], opens=[100.0, 100.0]).assign(volume=100_000.0)
    data = DataHandler({"TEST": bars}, ["TEST"])
    h = ImpactExecutionHandler(data, base_slippage_bps=0.0, impact_coef=100.0, commission_bps=0.0)
    data.update_bars()                                   # bar 0
    h.on_order(OrderEvent("TEST", "MKT", qty, "BUY"))
    data.update_bars()                                   # bar 1 -> fills at open
    return h.fill_pending()[0]


def test_larger_order_pays_more_impact(make_bars):
    small = _fill_for_qty(make_bars, 1_000)              # 1% of volume
    large = _fill_for_qty(make_bars, 10_000)             # 10% of volume
    assert large.fill_price > small.fill_price > 100.0   # both pay, big pays more
