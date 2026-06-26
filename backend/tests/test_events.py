from datetime import datetime, timezone

from backtest.events import FillEvent, MarketEvent, OrderEvent, SignalEvent

T = datetime(2024, 1, 1, tzinfo=timezone.utc)


def test_event_type_tags():
    assert MarketEvent(T).type == "MARKET"
    assert SignalEvent("X", T, "LONG").type == "SIGNAL"
    assert OrderEvent("X", "MKT", 10, "BUY").type == "ORDER"
    assert FillEvent("X", T, 10, "BUY", 100.0).type == "FILL"


def test_fill_signed_quantity():
    assert FillEvent("X", T, 10, "BUY", 100.0).signed_quantity == 10
    assert FillEvent("X", T, 10, "SELL", 100.0).signed_quantity == -10
