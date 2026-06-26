# Alpha / Strategy Module (Pillar 3 · Phase 3)

Pluggable strategies behind a common base class, so ideas compete on equal footing.

**Built so far (Phase 2.6):** `base.py` (`Strategy` ABC), `buy_and_hold.py`, and
`ma_crossover.py` — all run through the event-driven backtester. The richer
alpha below lands in Phase 3.

**Planned components**
- `Strategy` base class: `calculate_signals(market_event) -> list[SignalEvent]`.  ✅
- Mean reversion — cointegrated pairs (Engle-Granger), trade the spread Z-score.
- Cross-sectional momentum — rank a universe, long top / short bottom decile.
- Market making — quote both sides around mid, manage and skew on inventory.
- A strategy comparison report: return, Sharpe, max DD, turnover.

All strategies emit standardized `SignalEvent`s so the engine treats them identically.
