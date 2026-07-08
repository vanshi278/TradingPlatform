"""AI analyst + auto-trader. LLM is mocked; DB-backed parts skip if DB is down."""
import uuid
from unittest.mock import patch

import psycopg2
import pytest

from ai.analyst import analyze_symbol, compute_features, rule_based_analysis
from api.config import settings
from api.market_sim import SIM


def _db_available() -> bool:
    try:
        psycopg2.connect(settings.pg_dsn, connect_timeout=2).close()
        return True
    except Exception:
        return False


def _warm_sim(n=60):
    for _ in range(n):
        SIM.tick()


def test_features_computed_from_shared_sim():
    _warm_sim()
    f = compute_features("RELIANCE")
    assert f and f["symbol"] == "RELIANCE"
    assert 0 <= f["rsi_14"] <= 100
    assert f["price"] > 0


def test_rule_based_is_deterministic_and_structured():
    _warm_sim()
    f = compute_features("TCS")
    a1, a2 = rule_based_analysis(f), rule_based_analysis(f)
    assert a1 == a2
    assert a1["action"] in ("buy", "sell", "hold")
    assert 0 <= a1["confidence"] <= 1
    assert "rationale" in a1 and a1["provider"] == "rule-based"


def test_analyze_falls_back_when_llm_unavailable():
    _warm_sim()
    with patch("ai.analyst.gemini_analysis", return_value=None):
        out = analyze_symbol("INFY", use_llm=True)
    assert out["provider"] == "rule-based"


def test_analyze_uses_llm_result_when_valid():
    _warm_sim()
    fake = {"action": "buy", "confidence": 0.8, "rationale": "x", "risks": "y",
            "provider": "gemini (test)", "features": {}}
    with patch("ai.analyst.gemini_analysis", return_value=fake):
        out = analyze_symbol("INFY", use_llm=True)
    assert out["provider"] == "gemini (test)" and out["action"] == "buy"


@pytest.mark.skipif(not _db_available(), reason="TimescaleDB not reachable")
def test_auto_trader_decides_logs_and_orders():
    from ai.decisions import list_decisions
    from ai.trader import _decide_and_trade
    from auth.service import create_user
    from trading.engine import portfolio

    _warm_sim()
    uid = create_user(f"ai-{uuid.uuid4().hex[:10]}@example.com", "hunter22")["id"]

    forced = {"action": "buy", "confidence": 0.9, "rationale": "test buy signal",
              "risks": "", "provider": "rule-based", "features": {"f": 1}}
    with patch("ai.trader.analyze_symbol", return_value=forced):
        row = _decide_and_trade(uid, "RELIANCE", min_confidence=0.5, use_llm=False)

    assert row["action"] == "buy" and row["order_id"]
    assert portfolio(uid)["positions"][0]["symbol"] == "RELIANCE"

    log = list_decisions(uid)
    assert log and log[0]["symbol"] == "RELIANCE" and "test buy signal" in log[0]["rationale"]

    # a follow-up SELL flattens (long-only)
    forced_sell = dict(forced, action="sell", rationale="test sell")
    with patch("ai.trader.analyze_symbol", return_value=forced_sell):
        _decide_and_trade(uid, "RELIANCE", min_confidence=0.5, use_llm=False)
    assert portfolio(uid)["positions"] == []


@pytest.mark.skipif(not _db_available(), reason="TimescaleDB not reachable")
def test_low_confidence_logs_but_does_not_trade():
    from ai.decisions import list_decisions
    from ai.trader import _decide_and_trade
    from auth.service import create_user
    from trading.engine import portfolio

    _warm_sim()
    uid = create_user(f"ai-{uuid.uuid4().hex[:10]}@example.com", "hunter22")["id"]
    weak = {"action": "buy", "confidence": 0.2, "rationale": "weak", "risks": "",
            "provider": "rule-based", "features": {}}
    with patch("ai.trader.analyze_symbol", return_value=weak):
        row = _decide_and_trade(uid, "TCS", min_confidence=0.5, use_llm=False)
    assert row["order_id"] is None
    assert portfolio(uid)["positions"] == []
    assert list_decisions(uid)[0]["action"] == "buy"      # decision still logged
