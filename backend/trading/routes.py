"""Trading REST endpoints — all require a logged-in user."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.config import settings
from auth.deps import get_current_user
from trading import engine, store

router = APIRouter(prefix="/api/trading", tags=["trading"])


class PlaceOrder(BaseModel):
    symbol: str
    side: str                      # buy | sell
    qty: int = Field(gt=0, le=1_000_000)
    order_type: str = "market"     # market | limit
    limit_price: Optional[float] = None


@router.get("/mode")
def mode(user: dict = Depends(get_current_user)) -> dict:
    return {"mode": settings.trading_mode}


@router.post("/orders")
def place(body: PlaceOrder, user: dict = Depends(get_current_user)) -> dict:
    result = engine.place_order(
        user["id"], body.symbol, body.side, body.qty, body.order_type,
        body.limit_price, source="manual",
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/orders")
def orders(user: dict = Depends(get_current_user), limit: int = 100) -> dict:
    return {"orders": store.list_orders(user["id"], limit=limit)}


@router.delete("/orders/{order_id}")
def cancel(order_id: str, user: dict = Depends(get_current_user)) -> dict:
    result = engine.cancel_order(user["id"], order_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/portfolio")
def portfolio(user: dict = Depends(get_current_user)) -> dict:
    return engine.portfolio(user["id"])
