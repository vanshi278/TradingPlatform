"""The AI auto-trader — signals to risk-gated orders, with a full audit trail.

Per-user async loop: every `interval` seconds it analyzes each symbol, logs the
decision (action, confidence, rationale, features) to `ai_decisions`, and — when
confidence clears the threshold — places a paper order through the SAME
risk-gated engine as manual trading.

Design guardrails (deliberate):
  * Paper mode only. The auto-trader refuses to start when TRADING_MODE=live —
    autonomous real-money order flow is out of scope by design; in live mode
    the AI produces recommendations a human clicks to execute.
  * Long-only: buys open/add (capped per-symbol), sells only flatten.
  * Rule-based signals in the loop by default (deterministic, quota-free);
    Gemini narrative analysis is used for the on-demand /api/ai/analyze.
"""
from __future__ import annotations

import asyncio
import contextlib
from typing import Optional

from ai.analyst import analyze_symbol
from ai.decisions import insert_decision
from api.config import settings
from api.market_sim import SIM
from trading.engine import place_order, portfolio

MAX_POSITION_FRACTION = 0.10   # cap per-symbol exposure at 10% of equity
TRADE_FRACTION = 0.05          # each buy targets ~5% of equity

_sessions: dict[int, dict] = {}          # user_id -> {task, symbols, interval, ...}


def _decide_and_trade(user_id: int, symbol: str, min_confidence: float,
                      use_llm: bool) -> dict:
    """One decision for one symbol. Returns the log row (synchronous, runs in a
    thread from the async loop)."""
    analysis = analyze_symbol(symbol, use_llm=use_llm)
    if "error" in analysis:
        return analysis
    action, conf = analysis["action"], analysis["confidence"]

    pf = portfolio(user_id)
    held = {p["symbol"]: p for p in pf["positions"]}
    px = SIM.price(symbol) or 0.0
    order_id: Optional[str] = None
    note = ""

    if px > 0 and conf >= min_confidence:
        if action == "buy":
            current_value = held.get(symbol, {}).get("market_value", 0.0)
            if current_value < MAX_POSITION_FRACTION * pf["equity"]:
                qty = max(1, int(TRADE_FRACTION * pf["equity"] / px))
                res = place_order(user_id, symbol, "buy", qty, "market", source="ai")
                order_id = (res.get("order") or {}).get("id")
                note = f" -> bought {qty}" if res.get("fill") else " -> order not filled"
            else:
                note = " -> position cap reached, no add"
        elif action == "sell":
            qty = held.get(symbol, {}).get("qty", 0)
            if qty > 0:
                res = place_order(user_id, symbol, "sell", qty, "market", source="ai")
                order_id = (res.get("order") or {}).get("id")
                note = f" -> flattened {qty}" if res.get("fill") else " -> order not filled"
            else:
                note = " -> nothing to sell (long-only)"
    elif conf < min_confidence and action != "hold":
        note = f" -> below confidence threshold {min_confidence}"

    rationale = analysis["rationale"] + note
    insert_decision(user_id, symbol, action, conf, rationale, order_id,
                    analysis.get("features", {}))
    return {"symbol": symbol, "action": action, "confidence": conf,
            "rationale": rationale, "order_id": order_id}


async def _loop(user_id: int) -> None:
    while True:
        s = _sessions.get(user_id)
        if not s:
            return
        for symbol in s["symbols"]:
            try:
                await asyncio.to_thread(
                    _decide_and_trade, user_id, symbol, s["min_confidence"], s["use_llm"]
                )
            except Exception:  # noqa: BLE001 - a bad tick must not kill the loop
                pass
        await asyncio.sleep(s["interval"])


def start(user_id: int, symbols: Optional[list[str]] = None, interval: float = 5.0,
          min_confidence: float = 0.5, use_llm: bool = False) -> dict:
    if settings.trading_mode == "live":
        return {"error": "auto-trader runs in paper mode only (by design); "
                         "in live mode the AI gives recommendations you confirm"}
    stop(user_id)
    syms = [s.upper() for s in (symbols or SIM.symbols()) if SIM.price(s) is not None]
    if not syms:
        return {"error": "no valid symbols"}
    session = {
        "symbols": syms,
        "interval": max(2.0, float(interval)),
        "min_confidence": min(max(float(min_confidence), 0.0), 1.0),
        "use_llm": bool(use_llm),
    }
    # must be called from the event loop (async route), not a worker thread
    session["task"] = asyncio.get_running_loop().create_task(_loop(user_id))
    _sessions[user_id] = session
    return status(user_id)


def stop(user_id: int) -> dict:
    s = _sessions.pop(user_id, None)
    if s and (task := s.get("task")):
        task.cancel()
        with contextlib.suppress(Exception):
            pass
    return {"running": False}


def status(user_id: int) -> dict:
    s = _sessions.get(user_id)
    if not s:
        return {"running": False}
    return {"running": True, "symbols": s["symbols"], "interval": s["interval"],
            "min_confidence": s["min_confidence"], "use_llm": s["use_llm"]}
