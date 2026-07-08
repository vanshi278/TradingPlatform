"""AI endpoints: on-demand analysis, auto-trader control, decision log."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ai import trader
from ai.analyst import analyze_symbol
from ai.decisions import list_decisions
from api.config import settings
from auth.deps import get_current_user
from trading.engine import portfolio

router = APIRouter(prefix="/api/ai", tags=["ai"])


class AnalyzeRequest(BaseModel):
    symbol: str


class TraderStart(BaseModel):
    symbols: Optional[list[str]] = None
    interval: float = 5.0
    min_confidence: float = 0.5
    use_llm: bool = False


@router.post("/analyze")
def analyze(body: AnalyzeRequest, user: dict = Depends(get_current_user)) -> dict:
    pf = portfolio(user["id"])
    held = next((p for p in pf["positions"] if p["symbol"] == body.symbol.upper()), None)
    note = (f"currently long {held['qty']} @ avg {held['avg_cost']}"
            if held else "currently flat in this name")
    return analyze_symbol(body.symbol, portfolio_note=note, use_llm=True)


@router.get("/provider")
def provider(user: dict = Depends(get_current_user)) -> dict:
    return {
        "llm": bool(settings.gemini_api_key),
        "provider": f"gemini ({settings.gemini_model})" if settings.gemini_api_key
                    else "rule-based (set GEMINI_API_KEY for LLM analysis)",
    }


@router.post("/trader/start")
async def trader_start(body: TraderStart, user: dict = Depends(get_current_user)) -> dict:
    # async so trader.start() runs on the event loop and can create the task
    return trader.start(user["id"], body.symbols, body.interval,
                        body.min_confidence, body.use_llm)


@router.post("/trader/stop")
async def trader_stop(user: dict = Depends(get_current_user)) -> dict:
    return trader.stop(user["id"])


@router.get("/trader/status")
def trader_status(user: dict = Depends(get_current_user)) -> dict:
    return trader.status(user["id"])


@router.get("/decisions")
def decisions(user: dict = Depends(get_current_user), limit: int = 50) -> dict:
    return {"decisions": list_decisions(user["id"], limit=limit)}
