"""Trade the ML score (Phase 4.7).

Given the walk-forward *out-of-sample* predictions (a date × symbol score table),
rebalance monthly into a dollar-neutral book: long the top-quantile scores, short
the bottom. Because the scores are strictly OOS (each produced by a model trained
only on earlier folds), feeding them to the backtester introduces no leakage.
"""
from __future__ import annotations

import pandas as pd

from backtest.events import MarketEvent, SignalEvent
from strategies.base import Strategy


class MLStrategy(Strategy):
    def __init__(self, data, symbols, scores: pd.DataFrame, quantile: float = 0.3, gross: float = 1.0):
        super().__init__(data, symbols)
        self.scores = scores.sort_index()        # index = score date, columns = symbols
        self.quantile = quantile
        self.gross = gross
        self._used = set()

    def calculate_signals(self, event: MarketEvent):
        now = event.time
        available = self.scores.loc[self.scores.index <= now]
        if available.empty:
            return []
        score_date = available.index[-1]
        if score_date in self._used:
            return []                              # already rebalanced on this score
        self._used.add(score_date)

        row = available.iloc[-1].dropna()
        if len(row) < 4:
            return []
        ranked = row.sort_values()
        k = max(1, min(int(len(ranked) * self.quantile), len(ranked) // 2))
        longs = set(ranked.index[-k:])
        shorts = set(ranked.index[:k])
        weight = self.gross / (2 * k)

        signals = []
        for sym in row.index:
            if sym in longs:
                target = weight
            elif sym in shorts:
                target = -weight
            else:
                target = 0.0
            signals.append(SignalEvent(sym, now, "TARGET", target_pct=target))
        return signals
