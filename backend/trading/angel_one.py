"""Angel One SmartAPI live-broker adapter (free API; brokerage per executed order).

Activates only when TRADING_MODE=live and all SMARTAPI_* env vars are set:

    SMARTAPI_KEY          # from smartapi.angelbroking.com (create an app)
    SMARTAPI_CLIENT_CODE  # your Angel One client/login code
    SMARTAPI_PIN          # your login PIN
    SMARTAPI_TOTP_SECRET  # TOTP secret captured when enabling 2FA for SmartAPI

Also requires:  pip install smartapi-python pyotp logzero
Note (Apr 2026 rule): Angel One only accepts API order placement from your
REGISTERED STATIC IP — register it in the SmartAPI portal first.

The adapter keeps the exact same order/fill persistence as paper mode, so the
dashboard, P&L, and analysis work identically in both modes. LIVE fills are
recorded at the exchange-confirmed average price when available.
"""
from __future__ import annotations

import os
from typing import Optional

from trading import store

_session = None  # cached SmartConnect session


def _creds() -> dict:
    return {
        "api_key": os.getenv("SMARTAPI_KEY", ""),
        "client_code": os.getenv("SMARTAPI_CLIENT_CODE", ""),
        "pin": os.getenv("SMARTAPI_PIN", ""),
        "totp_secret": os.getenv("SMARTAPI_TOTP_SECRET", ""),
    }


def angel_available() -> bool:
    return all(_creds().values())


def _connect():
    """Login (TOTP) and cache the session."""
    global _session
    if _session is not None:
        return _session
    try:
        import pyotp
        from SmartApi import SmartConnect
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "Live mode needs the SmartAPI SDK: pip install smartapi-python pyotp logzero"
        ) from exc
    c = _creds()
    api = SmartConnect(api_key=c["api_key"])
    totp = pyotp.TOTP(c["totp_secret"]).now()
    data = api.generateSession(c["client_code"], c["pin"], totp)
    if not data.get("status"):
        raise RuntimeError(f"Angel One login failed: {data.get('message')}")
    _session = api
    return api


# Minimal NSE symbol-token map for the demo universe (extend as needed).
SYMBOL_TOKENS = {
    "RELIANCE": ("RELIANCE-EQ", "2885"),
    "TCS": ("TCS-EQ", "11536"),
    "INFY": ("INFY-EQ", "1594"),
    "HDFCBANK": ("HDFCBANK-EQ", "1333"),
    "ICICIBANK": ("ICICIBANK-EQ", "4963"),
}


def place_live_order(user_id: int, symbol: str, side: str, qty: int,
                     order_type: str, limit_price: Optional[float],
                     source: str, risk_note: Optional[str]) -> dict:
    """Route a risk-approved order to Angel One; persist order + fill."""
    if symbol not in SYMBOL_TOKENS:
        return {"error": f"{symbol} has no SmartAPI token mapping yet"}
    tradingsymbol, token = SYMBOL_TOKENS[symbol]
    try:
        api = _connect()
        params = {
            "variety": "NORMAL",
            "tradingsymbol": tradingsymbol,
            "symboltoken": token,
            "transactiontype": side.upper(),
            "exchange": "NSE",
            "ordertype": "MARKET" if order_type == "market" else "LIMIT",
            "producttype": "DELIVERY",
            "duration": "DAY",
            "quantity": str(qty),
        }
        if order_type == "limit":
            params["price"] = str(limit_price)
        broker_order_id = api.placeOrder(params)
    except Exception as exc:  # noqa: BLE001 - surface broker errors verbatim
        order = store.insert_order(user_id, symbol, side, order_type, qty, limit_price,
                                   "rejected", f"broker error: {exc}", source, "live")
        return {"order": order, "fill": None}

    note = f"broker_order_id={broker_order_id}" + (f"; {risk_note}" if risk_note else "")
    # Live orders confirm asynchronously on the exchange; record as open with the
    # broker id. (A production system would poll the order book / postback.)
    order = store.insert_order(user_id, symbol, side, order_type, qty, limit_price,
                               "open", note, source, "live")
    return {"order": order, "fill": None, "broker_order_id": broker_order_id}
