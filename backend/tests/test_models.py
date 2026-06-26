from datetime import datetime, timezone

from data.models import Side, Tick, to_utc


def test_tick_json_roundtrip():
    t = Tick(
        time=datetime(2024, 1, 1, 9, 15, tzinfo=timezone.utc),
        symbol="RELIANCE",
        price=2900.5,
        size=10.0,
        side=Side.BUY,
        source="feed-A",
    )
    assert Tick.from_json(t.to_json()) == t


def test_to_utc_assumes_naive_is_utc():
    assert to_utc(datetime(2024, 1, 1, 12, 0, 0)).tzinfo == timezone.utc


def test_to_utc_converts_aware():
    # 09:15 IST (+05:30) == 03:45 UTC
    from datetime import timedelta, timezone as tz

    ist = tz(timedelta(hours=5, minutes=30))
    out = to_utc(datetime(2024, 1, 1, 9, 15, tzinfo=ist))
    assert (out.hour, out.minute) == (3, 45)


def test_default_side_serializes_to_unknown():
    t = Tick(time=datetime.now(timezone.utc), symbol="X", price=1.0)
    assert t.to_dict()["side"] == "unknown"
