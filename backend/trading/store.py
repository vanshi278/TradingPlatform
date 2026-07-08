"""Persistence for orders and fills (positions are always derived from fills)."""
from __future__ import annotations

import uuid
from typing import Optional

from data.storage import get_conn

ORDER_COLS = ("id, user_id, symbol, side, order_type, qty, limit_price, status, "
              "reason, source, mode, created_at, updated_at")


def _order_row(row) -> dict:
    keys = [c.strip() for c in ORDER_COLS.split(",")]
    d = dict(zip(keys, row))
    d["created_at"] = str(d["created_at"])
    d["updated_at"] = str(d["updated_at"])
    return d


def insert_order(user_id: int, symbol: str, side: str, order_type: str, qty: int,
                 limit_price: Optional[float], status: str, reason: Optional[str],
                 source: str, mode: str) -> dict:
    oid = uuid.uuid4().hex
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            f"""INSERT INTO orders (id, user_id, symbol, side, order_type, qty,
                                    limit_price, status, reason, source, mode)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING {ORDER_COLS}""",
            (oid, user_id, symbol.upper(), side, order_type, qty,
             limit_price, status, reason, source, mode),
        )
        return _order_row(cur.fetchone())


def update_order_status(order_id: str, status: str, reason: Optional[str] = None) -> None:
    with get_conn() as conn, conn.cursor() as cur:
        if reason is None:
            cur.execute("UPDATE orders SET status=%s, updated_at=now() WHERE id=%s",
                        (status, order_id))
        else:
            cur.execute("UPDATE orders SET status=%s, reason=%s, updated_at=now() WHERE id=%s",
                        (status, reason, order_id))


def get_order(order_id: str, user_id: Optional[int] = None) -> Optional[dict]:
    with get_conn() as conn, conn.cursor() as cur:
        if user_id is None:
            cur.execute(f"SELECT {ORDER_COLS} FROM orders WHERE id=%s", (order_id,))
        else:
            cur.execute(f"SELECT {ORDER_COLS} FROM orders WHERE id=%s AND user_id=%s",
                        (order_id, user_id))
        row = cur.fetchone()
    return _order_row(row) if row else None


def list_orders(user_id: int, limit: int = 100) -> list[dict]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            f"SELECT {ORDER_COLS} FROM orders WHERE user_id=%s ORDER BY created_at DESC LIMIT %s",
            (user_id, limit),
        )
        return [_order_row(r) for r in cur.fetchall()]


def open_limit_orders() -> list[dict]:
    """All users' resting limit orders (for the fill sweep)."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(f"SELECT {ORDER_COLS} FROM orders "
                    "WHERE status='open' AND order_type='limit'")
        return [_order_row(r) for r in cur.fetchall()]


def insert_fill(order_id: str, user_id: int, symbol: str, side: str, qty: int,
                price: float, commission: float) -> None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO fills (order_id, user_id, symbol, side, qty, price, commission) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (order_id, user_id, symbol.upper(), side, qty, price, commission),
        )


def list_fills(user_id: int, limit: int = 500) -> list[dict]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT order_id, symbol, side, qty, price, commission, time "
            "FROM fills WHERE user_id=%s ORDER BY time ASC LIMIT %s",
            (user_id, limit),
        )
        cols = ["order_id", "symbol", "side", "qty", "price", "commission", "time"]
        out = []
        for r in cur.fetchall():
            d = dict(zip(cols, r))
            d["time"] = str(d["time"])
            out.append(d)
        return out
