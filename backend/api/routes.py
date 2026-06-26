"""REST routes for the dashboard (mounted under /api)."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from api.service import run_backtest

router = APIRouter(prefix="/api")


class BacktestRequest(BaseModel):
    symbols: str = "RELIANCE"
    strategy: str = "buyhold"
    start: str = "2018-01-01"
    end: str = "2024-01-01"
    short: int = 20
    long: int = 50
    lookback: int = 60
    capital: float = 100_000.0
    execution: str = "fixed"


@router.get("/strategies")
def strategies() -> dict:
    return {"strategies": ["buyhold", "ma", "pairs", "crosssec"]}


@router.post("/backtest/run")
def backtest_run(req: BacktestRequest) -> dict:
    return run_backtest(req.model_dump())
