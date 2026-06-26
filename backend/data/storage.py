"""TimescaleDB read/write helpers for the `bars` and `ticks` hypertables.

Thin psycopg2 wrappers, no ORM. Bulk inserts use execute_values; bars upsert on
their natural key so re-loading the same history is idempotent.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

from api.config import settings
from data.models import Tick

# repo root -> db/init.sql
_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "db" / "init.sql"

# Fail fast instead of blocking on an unreachable DB.
CONNECT_TIMEOUT = 5


def _f(v) -> Optional[float]:
    """Coerce to float, mapping NaN/None/garbage to None."""
    try:
        if v is None:
            return None
        f = float(v)
        return None if pd.isna(f) else f
    except (TypeError, ValueError):
        return None


@contextmanager
def get_conn():
    conn = psycopg2.connect(settings.pg_dsn, connect_timeout=CONNECT_TIMEOUT)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_schema(sql_path: Path | str | None = None) -> None:
    """Run db/init.sql (idempotent). Handy for tests / non-Docker setups."""
    path = Path(sql_path) if sql_path else _SCHEMA_PATH
    sql = path.read_text()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql)


def insert_bars(df: pd.DataFrame, interval: str = "1d") -> int:
    """Upsert a clean OHLCV frame (as returned by load_history) into `bars`.

    Returns the number of rows written.
    """
    if df is None or df.empty:
        return 0
    rows = [
        (
            idx.to_pydatetime(),
            row["symbol"],
            interval,
            _f(row.get("open")),
            _f(row.get("high")),
            _f(row.get("low")),
            _f(row.get("close")),
            _f(row.get("volume")),
        )
        for idx, row in df.iterrows()
    ]
    sql = """
        INSERT INTO bars (time, symbol, interval, open, high, low, close, volume)
        VALUES %s
        ON CONFLICT (symbol, interval, time) DO UPDATE SET
            open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low,
            close = EXCLUDED.close, volume = EXCLUDED.volume
    """
    with get_conn() as conn, conn.cursor() as cur:
        execute_values(cur, sql, rows)
    return len(rows)


def insert_ticks(ticks: Iterable[Tick]) -> int:
    """Bulk-insert normalized ticks into `ticks`. Returns rows written."""
    rows = [(t.time, t.symbol, t.price, t.size, t.side.value) for t in ticks]
    if not rows:
        return 0
    sql = "INSERT INTO ticks (time, symbol, price, size, side) VALUES %s"
    with get_conn() as conn, conn.cursor() as cur:
        execute_values(cur, sql, rows)
    return len(rows)


def query_bars(
    symbol: str,
    interval: str = "1d",
    start=None,
    end=None,
    limit: Optional[int] = None,
) -> pd.DataFrame:
    """Read bars back as a DataFrame indexed by tz-aware UTC time (ascending).

    With `limit`, returns the most recent `limit` bars (still ascending).
    """
    clauses = ["symbol = %s", "interval = %s"]
    params: list = [symbol.upper(), interval]
    if start is not None:
        clauses.append("time >= %s")
        params.append(str(start))
    if end is not None:
        clauses.append("time <= %s")
        params.append(str(end))
    where = " AND ".join(clauses)
    order = "DESC" if limit else "ASC"
    sql = (
        "SELECT time, symbol, open, high, low, close, volume "
        f"FROM bars WHERE {where} ORDER BY time {order}"
    )
    if limit:
        sql += " LIMIT %s"
        params.append(int(limit))

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        data = cur.fetchall()

    df = pd.DataFrame(data, columns=cols)
    if df.empty:
        return df
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df.sort_values("time").set_index("time")


def query_ticks(symbol: str, start=None, end=None, limit: Optional[int] = 1000) -> pd.DataFrame:
    """Read ticks back as a DataFrame indexed by tz-aware UTC time (ascending)."""
    clauses = ["symbol = %s"]
    params: list = [symbol.upper()]
    if start is not None:
        clauses.append("time >= %s")
        params.append(str(start))
    if end is not None:
        clauses.append("time <= %s")
        params.append(str(end))
    where = " AND ".join(clauses)
    sql = f"SELECT time, symbol, price, size, side FROM ticks WHERE {where} ORDER BY time DESC"
    if limit:
        sql += " LIMIT %s"
        params.append(int(limit))

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        data = cur.fetchall()

    df = pd.DataFrame(data, columns=cols)
    if df.empty:
        return df
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df.sort_values("time").set_index("time")
