"""TimescaleDB round-trip tests. Skipped automatically unless the DB is up
(`docker compose up -d timescaledb`)."""
from datetime import datetime, timezone

import pandas as pd
import psycopg2
import pytest

from api.config import settings
from data import storage
from data.models import Side, Tick


def _db_available() -> bool:
    """Real (short-timeout) Postgres connect, so the suite skips when the DB is
    down. A plain TCP probe is not enough: a stale port-forwarder can accept the
    socket without speaking Postgres."""
    try:
        psycopg2.connect(settings.pg_dsn, connect_timeout=2).close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _db_available(), reason="TimescaleDB not reachable (run: docker compose up -d timescaledb)"
)


def test_bars_roundtrip():
    storage.init_schema()
    idx = pd.to_datetime(["2024-01-01T00:00:00Z", "2024-01-02T00:00:00Z"])
    df = pd.DataFrame(
        {
            "open": [1.0, 2.0],
            "high": [2.0, 3.0],
            "low": [0.5, 1.5],
            "close": [1.5, 2.5],
            "volume": [100, 200],
            "symbol": ["ZZTEST", "ZZTEST"],
        },
        index=idx,
    )
    df.index.name = "time"

    assert storage.insert_bars(df, interval="1d") == 2
    # idempotent upsert
    assert storage.insert_bars(df, interval="1d") == 2

    back = storage.query_bars("ZZTEST", interval="1d")
    assert len(back) == 2
    assert pytest.approx(back["close"].iloc[-1]) == 2.5


def test_ticks_roundtrip():
    storage.init_schema()
    ticks = [
        Tick(
            time=datetime(2024, 1, 1, 9, 15, tzinfo=timezone.utc),
            symbol="ZZTICK",
            price=10.0 + i,
            size=5.0,
            side=Side.BUY,
            source="t",
        )
        for i in range(3)
    ]
    assert storage.insert_ticks(ticks) == 3
    back = storage.query_ticks("ZZTICK")
    assert len(back) >= 3
