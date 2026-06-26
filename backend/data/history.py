"""Historical OHLCV loader.

Phase 1 uses yfinance (no API key, works globally) as the historical source,
mapping bare NSE symbols to Yahoo tickers (RELIANCE -> RELIANCE.NS). A broker
historical API (Kite/Upstox) can later sit behind the same `load_history`
signature without anything downstream changing.
"""
from __future__ import annotations

import argparse
from datetime import datetime

import pandas as pd

NSE_TZ = "Asia/Kolkata"
OHLCV = ["open", "high", "low", "close", "volume"]


def to_yahoo_ticker(symbol: str) -> str:
    """Map a bare NSE symbol to a Yahoo Finance ticker.

    'RELIANCE' -> 'RELIANCE.NS'; already-suffixed ('TCS.NS') or index ('^NSEI')
    symbols pass through unchanged.
    """
    s = symbol.strip().upper()
    if s.startswith("^") or "." in s:
        return s
    return f"{s}.NS"


def _clean_ohlcv(df: pd.DataFrame, symbol: str, exchange_tz: str = NSE_TZ) -> pd.DataFrame:
    """Normalize a raw OHLCV frame: lowercase columns, UTC index, sorted,
    de-duplicated, no all-NaN rows. Pure (no network) so it is unit-testable.
    """
    if df is None or df.empty:
        empty = pd.DataFrame(columns=[*OHLCV, "symbol"])
        empty.index = pd.DatetimeIndex([], tz="UTC", name="time")
        return empty

    out = df.copy()
    out.columns = [str(c).lower() for c in out.columns]
    out = out[[c for c in OHLCV if c in out.columns]]

    # tz-normalize the index to UTC (daily bars come back tz-naive; intraday tz-aware)
    idx = pd.DatetimeIndex(out.index)
    idx = idx.tz_localize(exchange_tz) if idx.tz is None else idx
    out.index = idx.tz_convert("UTC")
    out.index.name = "time"

    out = out[~out.index.duplicated(keep="last")].sort_index()
    out = out.dropna(subset=["close"])
    out["symbol"] = symbol.strip().upper()
    return out


def load_history(
    symbol: str,
    start: str | datetime,
    end: str | datetime,
    interval: str = "1d",
    source: str = "yfinance",
) -> pd.DataFrame:
    """Load clean OHLCV history for one symbol.

    Returns a DataFrame indexed by tz-aware UTC timestamp with columns
    open, high, low, close, volume, symbol. Splits/dividends are auto-adjusted.

    Note: yfinance limits intraday history (e.g. 1m ~ last 7 days, <1d ~ 60 days).
    """
    if source != "yfinance":
        raise NotImplementedError(f"history source '{source}' is not wired yet")

    import yfinance as yf  # local import so the package imports even without yfinance

    ticker = to_yahoo_ticker(symbol)
    raw = yf.Ticker(ticker).history(
        start=str(start), end=str(end), interval=interval, auto_adjust=True
    )
    return _clean_ohlcv(raw, symbol)


def load_history_many(
    symbols, start, end, interval: str = "1d", source: str = "yfinance"
) -> pd.DataFrame:
    """Load several symbols and concatenate into one long-format frame."""
    frames = [load_history(s, start, end, interval, source) for s in symbols]
    frames = [f for f in frames if not f.empty]
    return pd.concat(frames).sort_index() if frames else pd.DataFrame()


def _main() -> None:
    p = argparse.ArgumentParser(description="Load historical OHLCV via yfinance")
    p.add_argument("--symbol", default="RELIANCE")
    p.add_argument("--start", default="2022-01-01")
    p.add_argument("--end", default="2024-01-01")
    p.add_argument("--interval", default="1d")
    args = p.parse_args()

    df = load_history(args.symbol, args.start, args.end, args.interval)
    if df.empty:
        print(f"{args.symbol}: no data returned")
        return
    print(f"{args.symbol}: {len(df)} bars  [{df.index.min()} .. {df.index.max()}]")
    print(df.head())
    print("...")
    print(df.tail())


if __name__ == "__main__":
    _main()
