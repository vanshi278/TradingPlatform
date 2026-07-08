"""AI market analyst.

Two providers behind one interface:
  * GeminiProvider    — Google Gemini (free-tier API key) for narrative analysis
  * RuleBasedProvider — deterministic, transparent signal built from the same
                        features; also the fallback whenever Gemini is
                        unavailable, errors, or returns malformed output

Both consume the same feature snapshot computed from the shared market
simulator, and both return the same structured dict:

    {action: buy|sell|hold, confidence: 0..1, rationale: str,
     risks: str, provider: str, features: {...}}
"""
from __future__ import annotations

import json
import math
from statistics import pstdev
from typing import Optional

from api.config import settings
from api.market_sim import SIM


# ---- features ---------------------------------------------------------------
def rsi(series: list[float], period: int = 14) -> float:
    if len(series) < period + 1:
        return 50.0
    gains = losses = 0.0
    for a, b in zip(series[-period - 1:-1], series[-period:]):
        d = b - a
        gains += max(d, 0.0)
        losses += max(-d, 0.0)
    if losses == 0:
        return 100.0
    rs = gains / losses
    return 100.0 - 100.0 / (1.0 + rs)


def compute_features(symbol: str) -> Optional[dict]:
    s = SIM.series(symbol, 300)
    if len(s) < 30:
        return None
    px = s[-1]
    mom_short = px / s[-min(20, len(s))] - 1.0
    mom_long = px / s[0] - 1.0
    rets = [b / a - 1.0 for a, b in zip(s[:-1], s[1:])]
    vol = pstdev(rets) * math.sqrt(len(rets)) if len(rets) > 2 else 0.0
    lo, hi = min(s), max(s)
    return {
        "symbol": symbol.upper(),
        "price": round(px, 2),
        "mom_short_pct": round(mom_short * 100, 3),
        "mom_long_pct": round(mom_long * 100, 3),
        "rsi_14": round(rsi(s), 1),
        "volatility_pct": round(vol * 100, 3),
        "range_pos": round((px - lo) / (hi - lo), 3) if hi > lo else 0.5,
        "n_ticks": len(s),
    }


# ---- rule-based provider (and fallback) --------------------------------------
def rule_based_analysis(feat: dict, portfolio_note: str = "") -> dict:
    score = 0.0
    parts = []
    if feat["mom_short_pct"] > 0.05:
        score += 0.5
        parts.append(f"short-term momentum is positive ({feat['mom_short_pct']:+.2f}%)")
    elif feat["mom_short_pct"] < -0.05:
        score -= 0.5
        parts.append(f"short-term momentum is negative ({feat['mom_short_pct']:+.2f}%)")
    if feat["mom_long_pct"] > 0:
        score += 0.3
        parts.append(f"longer trend is up ({feat['mom_long_pct']:+.2f}%)")
    else:
        score -= 0.3
        parts.append(f"longer trend is down ({feat['mom_long_pct']:+.2f}%)")
    if feat["rsi_14"] < 30:
        score += 0.2
        parts.append(f"RSI {feat['rsi_14']} is oversold (mean-reversion tailwind)")
    elif feat["rsi_14"] > 70:
        score -= 0.2
        parts.append(f"RSI {feat['rsi_14']} is overbought (mean-reversion headwind)")

    action = "buy" if score >= 0.3 else "sell" if score <= -0.3 else "hold"
    return {
        "action": action,
        "confidence": round(min(abs(score), 1.0), 2),
        "rationale": f"{feat['symbol']} @ {feat['price']}: " + "; ".join(parts) +
                     (f". {portfolio_note}" if portfolio_note else ""),
        "risks": f"tick volatility {feat['volatility_pct']:.2f}%; signal flips quickly "
                 "at this horizon; simulated market data.",
        "provider": "rule-based",
        "features": feat,
    }


# ---- Gemini provider ----------------------------------------------------------
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

PROMPT = """You are a cautious quantitative trading analyst. Given this market
snapshot (from a simulated NSE feed) and portfolio context, decide buy, sell, or
hold for the symbol. Reply with STRICT JSON only, no markdown fences:
{{"action": "buy|sell|hold", "confidence": <0..1>, "rationale": "<=60 words>",
"risks": "<=40 words"}}

Snapshot: {snapshot}
Portfolio: {portfolio}"""


def gemini_analysis(feat: dict, portfolio_note: str = "") -> Optional[dict]:
    """One Gemini call; None on any failure (caller falls back to rules)."""
    if not settings.gemini_api_key:
        return None
    try:
        import requests

        url = GEMINI_URL.format(model=settings.gemini_model)
        body = {
            "contents": [{"parts": [{"text": PROMPT.format(
                snapshot=json.dumps(feat), portfolio=portfolio_note or "flat")}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 300},
        }
        r = requests.post(url, params={"key": settings.gemini_api_key},
                          json=body, timeout=12)
        r.raise_for_status()
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        if text.startswith("```"):
            text = text.strip("`").removeprefix("json").strip()
        out = json.loads(text)
        action = str(out.get("action", "hold")).lower()
        if action not in ("buy", "sell", "hold"):
            return None
        return {
            "action": action,
            "confidence": max(0.0, min(float(out.get("confidence", 0.5)), 1.0)),
            "rationale": str(out.get("rationale", ""))[:600],
            "risks": str(out.get("risks", ""))[:400],
            "provider": f"gemini ({settings.gemini_model})",
            "features": feat,
        }
    except Exception:  # noqa: BLE001 - any failure -> rule-based fallback
        return None


def analyze_symbol(symbol: str, portfolio_note: str = "", use_llm: bool = True) -> dict:
    feat = compute_features(symbol)
    if feat is None:
        return {"error": f"not enough market history for {symbol} yet"}
    if use_llm:
        out = gemini_analysis(feat, portfolio_note)
        if out is not None:
            return out
    return rule_based_analysis(feat, portfolio_note)
