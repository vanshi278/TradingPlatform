"""Run a backtest end-to-end and report results.

    # buy & hold on real NSE data (yfinance, no Docker needed)
    cd backend && python -m backtest.run_backtest --symbols RELIANCE --strategy buyhold

    # 20/50 moving-average crossover
    cd backend && python -m backtest.run_backtest --symbols RELIANCE \
        --strategy ma --short 20 --long 50 --start 2018-01-01 --end 2024-01-01

Data comes from yfinance by default, or from TimescaleDB with --source db.
Equity curve CSV + PNG are written to results/ (gitignored).
"""
from __future__ import annotations

import argparse
from pathlib import Path

from backtest.data import DataHandler
from backtest.engine import Backtest
from backtest.execution import SimulatedExecutionHandler
from backtest.performance import compute_metrics, format_metrics
from backtest.portfolio import Portfolio
from strategies import BuyAndHold, MACrossover

RESULTS_DIR = Path(__file__).resolve().parents[2] / "results"


def _load_bars(symbols, start, end, interval, source):
    bars = {}
    if source == "yfinance":
        from data.history import load_history

        for s in symbols:
            df = load_history(s, start, end, interval)
            if not df.empty:
                bars[s] = df
    elif source == "db":
        from data.storage import query_bars

        for s in symbols:
            df = query_bars(s, interval=interval, start=start, end=end)
            if not df.empty:
                bars[s] = df
    else:
        raise ValueError(f"unknown source: {source}")
    return bars


def _build_strategy(name, data, symbols, short, long):
    if name == "buyhold":
        return BuyAndHold(data, symbols)
    if name == "ma":
        return MACrossover(data, symbols, short_window=short, long_window=long)
    raise ValueError(f"unknown strategy: {name} (choose buyhold|ma)")


def _save_outputs(equity_df, label):
    RESULTS_DIR.mkdir(exist_ok=True)
    csv_path = RESULTS_DIR / f"{label}_equity.csv"
    equity_df.to_csv(csv_path)

    png_path = RESULTS_DIR / f"{label}_equity.png"
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True, height_ratios=[3, 1])
        ax1.plot(equity_df.index, equity_df["equity"], color="#2563eb")
        ax1.set_title(label)
        ax1.set_ylabel("equity (×)")
        ax1.grid(alpha=0.3)
        dd = equity_df["total"] / equity_df["total"].cummax() - 1.0
        ax2.fill_between(equity_df.index, dd, 0, color="#dc2626", alpha=0.4)
        ax2.set_ylabel("drawdown")
        ax2.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(png_path, dpi=110)
        plt.close(fig)
    except Exception as exc:  # noqa: BLE001
        png_path = f"(plot skipped: {exc})"
    return csv_path, png_path


def main() -> None:
    p = argparse.ArgumentParser(description="AlphaForge event-driven backtest")
    p.add_argument("--symbols", default="RELIANCE", help="comma-separated, e.g. RELIANCE,TCS")
    p.add_argument("--strategy", default="buyhold", choices=["buyhold", "ma"])
    p.add_argument("--short", type=int, default=20)
    p.add_argument("--long", type=int, default=50)
    p.add_argument("--start", default="2018-01-01")
    p.add_argument("--end", default="2024-01-01")
    p.add_argument("--interval", default="1d")
    p.add_argument("--source", default="yfinance", choices=["yfinance", "db"])
    p.add_argument("--capital", type=float, default=100_000.0)
    p.add_argument("--periods", type=int, default=252, help="periods/year for annualization")
    args = p.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    bars = _load_bars(symbols, args.start, args.end, args.interval, args.source)
    if not bars:
        print("No data loaded — check symbols/dates/source.")
        return
    symbols = list(bars)

    data = DataHandler(bars, symbols)
    strategy = _build_strategy(args.strategy, data, symbols, args.short, args.long)
    portfolio = Portfolio(data, symbols, initial_capital=args.capital)
    execution = SimulatedExecutionHandler(data)

    portfolio = Backtest(data, strategy, portfolio, execution).run()
    equity_df = portfolio.equity_curve()
    metrics = compute_metrics(equity_df, periods_per_year=args.periods)

    label = f"{args.strategy}_{'-'.join(symbols)}_{args.interval}"
    csv_path, png_path = _save_outputs(equity_df, label)

    print(f"\n=== {label} | {args.start} .. {args.end} ===")
    print(format_metrics(metrics))
    print(f"  trades       : {len(portfolio.trades):>14d}")
    print(f"\nequity csv: {csv_path}")
    print(f"equity png: {png_path}")


if __name__ == "__main__":
    main()
