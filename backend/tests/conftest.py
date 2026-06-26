import pandas as pd
import pytest


@pytest.fixture
def make_bars():
    """Build a clean OHLCV frame from a list of closes (UTC daily index)."""

    def _make(closes, opens=None, start="2024-01-01", freq="D", symbol="TEST"):
        idx = pd.date_range(start, periods=len(closes), freq=freq, tz="UTC")
        o = list(opens) if opens is not None else list(closes)
        df = pd.DataFrame(
            {
                "open": o,
                "high": [max(a, b) for a, b in zip(o, closes)],
                "low": [min(a, b) for a, b in zip(o, closes)],
                "close": list(closes),
                "volume": [1000] * len(closes),
                "symbol": symbol,
            },
            index=idx,
        )
        df.index.name = "time"
        return df

    return _make
