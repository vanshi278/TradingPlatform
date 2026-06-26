import numpy as np
import pandas as pd
import pytest

from data.history import _clean_ohlcv, to_yahoo_ticker


def test_to_yahoo_ticker():
    assert to_yahoo_ticker("reliance") == "RELIANCE.NS"
    assert to_yahoo_ticker("TCS.NS") == "TCS.NS"
    assert to_yahoo_ticker("^NSEI") == "^NSEI"


def test_clean_ohlcv_normalizes():
    # unsorted index, a duplicate day, a NaN-close row, mixed-case columns
    idx = pd.to_datetime(["2024-01-03", "2024-01-01", "2024-01-02", "2024-01-02"])
    raw = pd.DataFrame(
        {
            "Open": [10, 11, 12, 12],
            "High": [11, 12, 13, 13],
            "Low": [9, 10, 11, 11],
            "Close": [10.5, np.nan, 12.5, 12.6],
            "Volume": [100, 200, 300, 300],
        },
        index=idx,
    )
    out = _clean_ohlcv(raw, "reliance")

    # columns lowercased, symbol appended
    assert list(out.columns) == ["open", "high", "low", "close", "volume", "symbol"]
    # tz-aware UTC index, sorted ascending
    assert str(out.index.tz) == "UTC"
    assert out.index.is_monotonic_increasing
    assert (out["symbol"] == "RELIANCE").all()
    # NaN-close row dropped; duplicate day collapsed to its last value (12.6).
    # Daily midnight IST converts to prior-day 18:30 UTC, so order is 01-02, 01-03.
    assert out["close"].tolist() == pytest.approx([12.6, 10.5])


def test_clean_ohlcv_empty():
    out = _clean_ohlcv(pd.DataFrame(), "TCS")
    assert out.empty
    assert str(out.index.tz) == "UTC"
