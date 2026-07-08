"""Paper-trading OMS lifecycle against the live DB (skips if DB down)."""
import uuid

import psycopg2
import pytest

from api.config import settings
from api.market_sim import SIM


def _db_available() -> bool:
    try:
        psycopg2.connect(settings.pg_dsn, connect_timeout=2).close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _db_available(), reason="TimescaleDB not reachable (run: docker compose up -d timescaledb)"
)


@pytest.fixture()
def user_id():
    from auth.service import create_user

    return create_user(f"trader-{uuid.uuid4().hex[:10]}@example.com", "hunter22")["id"]


def test_market_order_fills_and_updates_portfolio(user_id):
    from trading.engine import INITIAL_CASH, place_order, portfolio

    px = SIM.price("RELIANCE")
    res = place_order(user_id, "RELIANCE", "buy", 10, "market")
    assert res["order"]["status"] == "filled"
    fill = res["fill"]
    assert fill["qty"] == 10
    assert fill["price"] == pytest.approx(px, rel=0.001)      # ~2bps slippage

    pf = portfolio(user_id)
    assert pf["positions"][0]["symbol"] == "RELIANCE"
    assert pf["positions"][0]["qty"] == 10
    assert pf["cash"] < INITIAL_CASH                          # paid for the shares
    assert pf["equity"] == pytest.approx(INITIAL_CASH, rel=0.001)


def test_roundtrip_realizes_pnl(user_id):
    from trading.engine import place_order, portfolio

    place_order(user_id, "TCS", "buy", 5, "market")
    place_order(user_id, "TCS", "sell", 5, "market")
    pf = portfolio(user_id)
    assert pf["positions"] == []                              # flat again
    assert pf["realized_pnl"] == pytest.approx(0.0, abs=50)   # only spread+fees


def test_far_limit_rests_then_cancels(user_id):
    from trading.engine import cancel_order, place_order

    px = SIM.price("INFY")
    res = place_order(user_id, "INFY", "buy", 5, "limit", limit_price=round(px * 0.5, 2))
    assert res["order"]["status"] == "open" and res["fill"] is None

    out = cancel_order(user_id, res["order"]["id"])
    assert out["order"]["status"] == "cancelled"
    # cancelling twice fails cleanly
    assert "error" in cancel_order(user_id, res["order"]["id"])


def test_marketable_limit_fills_at_limit_or_better(user_id):
    from trading.engine import place_order

    px = SIM.price("HDFCBANK")
    res = place_order(user_id, "HDFCBANK", "buy", 5, "limit", limit_price=round(px * 1.05, 2))
    assert res["order"]["status"] == "filled"
    assert res["fill"]["price"] <= round(px * 1.05, 2)


def test_sweep_fills_resting_limit_when_price_crosses(user_id):
    from trading.engine import place_order, sweep_open_limit_orders
    from trading.store import get_order

    px = SIM.price("ICICIBANK")
    res = place_order(user_id, "ICICIBANK", "buy", 5, "limit", limit_price=round(px * 0.9, 2))
    assert res["order"]["status"] == "open"

    SIM.px["ICICIBANK"] = px * 0.85                            # crash through the limit
    try:
        assert sweep_open_limit_orders() >= 1
        assert get_order(res["order"]["id"])["status"] == "filled"
    finally:
        SIM.px["ICICIBANK"] = px                               # restore


def test_risk_gate_resizes_oversized_order(user_id):
    from trading.engine import place_order

    px = SIM.price("RELIANCE")
    huge = int(3_000_000 / px)                                 # ~3x equity in one name
    res = place_order(user_id, "RELIANCE", "buy", huge, "market")
    assert res["order"]["reason"] and "resized" in res["order"]["reason"]
    assert res["fill"]["qty"] < huge                           # capped at 25% of equity


def test_routes_require_auth():
    from fastapi.testclient import TestClient

    from api.main import app

    c = TestClient(app)
    assert c.get("/api/trading/portfolio").status_code == 401
    assert c.post("/api/trading/orders",
                  json={"symbol": "TCS", "side": "buy", "qty": 1}).status_code == 401


def test_routes_place_and_read_with_token():
    from fastapi.testclient import TestClient

    from api.main import app

    c = TestClient(app)
    email = f"api-{uuid.uuid4().hex[:10]}@example.com"
    token = c.post("/api/auth/signup",
                   json={"email": email, "password": "hunter22"}).json()["token"]
    h = {"Authorization": f"Bearer {token}"}

    r = c.post("/api/trading/orders", headers=h,
               json={"symbol": "TCS", "side": "buy", "qty": 3})
    assert r.status_code == 200 and r.json()["order"]["status"] == "filled"

    pf = c.get("/api/trading/portfolio", headers=h).json()
    assert pf["positions"][0]["qty"] == 3
    assert c.get("/api/trading/orders", headers=h).json()["orders"][0]["symbol"] == "TCS"
