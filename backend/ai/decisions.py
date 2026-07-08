"""Persistence for the AI trader's decision log — every signal, order or not."""
from __future__ import annotations

import json
from typing import Optional

from data.storage import get_conn


def insert_decision(user_id: int, symbol: str, action: str, confidence: float,
                    rationale: str, order_id: Optional[str], features: dict) -> None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO ai_decisions (user_id, symbol, action, confidence, rationale, "
            "order_id, features) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (user_id, symbol.upper(), action, confidence, rationale, order_id,
             json.dumps(features)),
        )


def list_decisions(user_id: int, limit: int = 50) -> list[dict]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT time, symbol, action, confidence, rationale, order_id "
            "FROM ai_decisions WHERE user_id=%s ORDER BY time DESC LIMIT %s",
            (user_id, limit),
        )
        cols = ["time", "symbol", "action", "confidence", "rationale", "order_id"]
        out = []
        for r in cur.fetchall():
            d = dict(zip(cols, r))
            d["time"] = str(d["time"])
            out.append(d)
        return out
