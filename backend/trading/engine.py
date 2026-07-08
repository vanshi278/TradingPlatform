"""The order-management engine.

place_order():  risk gate (Phase 6 RiskManager) -> broker execution -> persist.
Positions, cash, and P&L are always DERIVED from the fills table, so there is
no state to drift out of sync. Paper mode fills against the shared market
simulator; live mode routes to the Angel One adapter (same interface).

Every user gets a paper account with INITIAL_CASH; equity = cash + marked book.
"""
from __future__ import annotations

from typing import Optional

from api.config import settings
from api.market_sim import SIM
from risk.limits import RiskLimits, RiskManager
from trading import store

INITIAL_CASH = 1_000_000.0
COMMISSION_BPS = 2.0          # per executed order (paper)
SLIPPAGE_BPS = 2.0            # market orders cross the spread (paper)

SECTOR_MAP = {
    "RELIANCE": "energy",
    "TCS": "it", "INFY": "it",
    "HDFCBANK": "banks", "ICICIBANK": "banks",
}

RISK = RiskManager(
    RiskLimits(max_position_pct=0.25, max_sector_pct=0.40, max_gross_pct=2.0),
    sector_map=SECTOR_MAP,
)


# ---- positions / P&L (derived from fills) ----------------------------------
def portfolio(user_id: int) -> dict:
    """Positions with avg cost + realized/unrealized P&L, cash and equity."""
    fills = store.list_fills(user_id)
    cash = INITIAL_CASH
    pos: dict[str, dict] = {}          # symbol -> {qty, avg_cost, realized}

    for f in fills:
        sym, qty, px, side = f["symbol"], f["qty"], f["price"], f["side"]
        signed = qty if side == "buy" else -qty
        cash += (-px * qty - f["commission"]) if side == "buy" else (px * qty - f["commission"])

        p = pos.setdefault(sym, {"qty": 0, "avg_cost": 0.0, "realized": 0.0})
        old = p["qty"]
        new = old + signed
        if old == 0 or (old > 0) == (signed > 0):
            # opening or adding: weighted-average entry
            p["avg_cost"] = ((abs(old) * p["avg_cost"]) + (abs(signed) * px)) / max(abs(new), 1)
        else:
            closed = min(abs(old), abs(signed))
            direction = 1 if old > 0 else -1          # +1 closing a long, -1 a short
            p["realized"] += closed * (px - p["avg_cost"]) * direction
            if abs(signed) > abs(old):                # flipped through zero
                p["avg_cost"] = px
        p["qty"] = new
        if new == 0:
            p["avg_cost"] = 0.0

    marks = SIM.prices()
    positions, mkt_value, unrealized, realized = [], 0.0, 0.0, 0.0
    for sym, p in pos.items():
        mark = marks.get(sym, p["avg_cost"])
        upnl = p["qty"] * (mark - p["avg_cost"])
        realized += p["realized"]
        if p["qty"] != 0:
            mkt_value += p["qty"] * mark
            unrealized += upnl
            positions.append({
                "symbol": sym, "qty": p["qty"],
                "avg_cost": round(p["avg_cost"], 2), "mark": round(mark, 2),
                "market_value": round(p["qty"] * mark, 2),
                "unrealized_pnl": round(upnl, 2),
                "realized_pnl": round(p["realized"], 2),
            })

    equity = cash + mkt_value
    return {
        "cash": round(cash, 2),
        "equity": round(equity, 2),
        "market_value": round(mkt_value, 2),
        "unrealized_pnl": round(unrealized, 2),
        "realized_pnl": round(realized, 2),
        "total_pnl": round(equity - INITIAL_CASH, 2),
        "initial_cash": INITIAL_CASH,
        "positions": sorted(positions, key=lambda r: r["symbol"]),
    }


def _positions_qty(user_id: int) -> dict[str, int]:
    return {p["symbol"]: p["qty"] for p in portfolio(user_id)["positions"]}


# ---- execution --------------------------------------------------------------
def _paper_fill_price(symbol: str, side: str, order_type: str,
                      limit_price: Optional[float]) -> Optional[float]:
    """Fill price now, or None if a limit order isn't marketable yet."""
    px = SIM.price(symbol)
    if px is None:
        return None
    if order_type == "market":
        slip = SLIPPAGE_BPS / 1e4
        return round(px * (1 + slip) if side == "buy" else px * (1 - slip), 2)
    # limit: marketable-or-rest, filled at limit-or-better
    if side == "buy" and px <= limit_price:
        return round(min(px, limit_price), 2)
    if side == "sell" and px >= limit_price:
        return round(max(px, limit_price), 2)
    return None


def place_order(user_id: int, symbol: str, side: str, qty: int,
                order_type: str = "market", limit_price: Optional[float] = None,
                source: str = "manual") -> dict:
    """Full lifecycle: validate -> risk gate -> execute/rest -> persist."""
    symbol = symbol.upper()
    side = side.lower()
    order_type = order_type.lower()
    if side not in ("buy", "sell") or order_type not in ("market", "limit"):
        return {"error": "side must be buy/sell; order_type market/limit"}
    if qty <= 0:
        return {"error": "qty must be positive"}
    if order_type == "limit" and (limit_price is None or limit_price <= 0):
        return {"error": "limit orders need a positive limit_price"}
    px = SIM.price(symbol)
    if px is None:
        return {"error": f"unknown symbol {symbol} (tradable: {', '.join(SIM.symbols())})"}

    mode = settings.trading_mode
    if mode == "live":
        from trading.angel_one import angel_available
        if not angel_available():
            return {"error": "TRADING_MODE=live but Angel One credentials are missing"}

    # ---- pre-trade risk gate (Phase 6) ----
    snap = portfolio(user_id)
    signed = qty if side == "buy" else -qty
    ref_px = limit_price if order_type == "limit" else px
    approved, verdict = RISK.check_order(
        symbol, signed, ref_px, _positions_qty(user_id), SIM.prices(), snap["equity"],
    )
    if verdict == "blocked" or approved == 0:
        order = store.insert_order(user_id, symbol, side, order_type, qty, limit_price,
                                   "rejected", "risk limit: order blocked", source, mode)
        return {"order": order, "fill": None}
    risk_note = None
    if verdict == "resized":
        risk_note = f"risk limit: resized {qty} -> {abs(approved)}"
        qty = abs(approved)

    # ---- execute ----
    if mode == "live":
        from trading.angel_one import place_live_order
        return place_live_order(user_id, symbol, side, qty, order_type,
                                limit_price, source, risk_note)

    fill_px = _paper_fill_price(symbol, side, order_type, limit_price)
    if fill_px is None:                                    # rests on the book
        order = store.insert_order(user_id, symbol, side, order_type, qty, limit_price,
                                   "open", risk_note, source, mode)
        return {"order": order, "fill": None}

    commission = round(COMMISSION_BPS / 1e4 * fill_px * qty, 2)
    order = store.insert_order(user_id, symbol, side, order_type, qty, limit_price,
                               "filled", risk_note, source, mode)
    store.insert_fill(order["id"], user_id, symbol, side, qty, fill_px, commission)
    fill = {"price": fill_px, "qty": qty, "commission": commission}
    return {"order": order, "fill": fill}


def cancel_order(user_id: int, order_id: str) -> dict:
    order = store.get_order(order_id, user_id)
    if order is None:
        return {"error": "order not found"}
    if order["status"] != "open":
        return {"error": f"order is {order['status']}, not open"}
    store.update_order_status(order_id, "cancelled")
    return {"order": store.get_order(order_id, user_id)}


def sweep_open_limit_orders() -> int:
    """Fill any resting limit orders that have become marketable. Returns fills."""
    n = 0
    for order in store.open_limit_orders():
        fill_px = _paper_fill_price(order["symbol"], order["side"], "limit",
                                    order["limit_price"])
        if fill_px is None:
            continue
        commission = round(COMMISSION_BPS / 1e4 * fill_px * order["qty"], 2)
        store.insert_fill(order["id"], order["user_id"], order["symbol"],
                          order["side"], order["qty"], fill_px, commission)
        store.update_order_status(order["id"], "filled")
        n += 1
    return n
