"""Backtest service used by the REST API — runs the engine and returns JSON the
dashboard can render directly (equity/drawdown series, metrics, positions, risk).
"""
from __future__ import annotations

from backtest.data import DataHandler
from backtest.engine import Backtest
from backtest.execution import ImpactExecutionHandler, SimulatedExecutionHandler
from backtest.performance import compute_metrics
from backtest.portfolio import Portfolio
from data.history import load_history
from risk.var import historical_var, parametric_var
from strategies import BuyAndHold, CrossSectionalMomentum, MACrossover, PairsTradingStrategy


def _build_strategy(name, data, symbols, p):
    if name == "buyhold":
        return BuyAndHold(data, symbols)
    if name == "ma":
        return MACrossover(data, symbols, p.get("short", 20), p.get("long", 50))
    if name == "pairs":
        if len(symbols) != 2:
            raise ValueError("pairs needs exactly two symbols")
        return PairsTradingStrategy(data, symbols[0], symbols[1], lookback=p.get("lookback", 60))
    if name == "crosssec":
        return CrossSectionalMomentum(data, symbols, lookback=p.get("lookback", 126))
    raise ValueError(f"unknown strategy: {name}")


def _downsample(index, values, n=300):
    step = max(1, len(index) // n)
    return [
        {"time": t.strftime("%Y-%m-%d"), "value": round(float(v), 4)}
        for t, v in zip(index[::step], values[::step])
    ]


def run_backtest(params: dict) -> dict:
    symbols = [s.strip().upper() for s in params.get("symbols", "RELIANCE").split(",") if s.strip()]
    start = params.get("start", "2018-01-01")
    end = params.get("end", "2024-01-01")

    bars = {}
    for s in symbols:
        df = load_history(s, start, end, "1d")
        if not df.empty:
            bars[s] = df
    if not bars:
        return {"error": "no data for those symbols/dates"}
    symbols = list(bars)

    data = DataHandler(bars, symbols)
    strategy = _build_strategy(params.get("strategy", "buyhold"), data, symbols, params)
    portfolio = Portfolio(data, symbols, initial_capital=float(params.get("capital", 100_000)))
    execution = (
        ImpactExecutionHandler(data) if params.get("execution") == "impact"
        else SimulatedExecutionHandler(data)
    )
    portfolio = Backtest(data, strategy, portfolio, execution).run()

    eq = portfolio.equity_curve()
    if eq.empty:
        return {"error": "empty equity curve"}
    metrics = compute_metrics(eq)
    drawdown = eq["total"] / eq["total"].cummax() - 1.0
    rets = eq["returns"].to_numpy()

    return {
        "symbols": symbols,
        "strategy": params.get("strategy", "buyhold"),
        "metrics": {k: round(float(v), 4) for k, v in metrics.items()},
        "equity": _downsample(eq.index, eq["equity"].to_numpy()),
        "drawdown": _downsample(eq.index, drawdown.to_numpy()),
        "positions": [{"symbol": s, "shares": int(q)} for s, q in portfolio.positions.items() if q != 0],
        "trades": len(portfolio.trades),
        "risk": {
            "var_99": round(float(historical_var(rets, 0.99) * portfolio.initial_capital), 2),
            "var_param_99": round(float(parametric_var(rets, 0.99) * portfolio.initial_capital), 2),
            "max_drawdown": round(float(drawdown.min()), 4),
            "kill_switch": bool(drawdown.min() <= -0.25),    # would a -25% breaker have tripped?
        },
    }
