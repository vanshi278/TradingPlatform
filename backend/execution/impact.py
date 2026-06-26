"""Linear (Kyle's-lambda style) price-impact model (Phase 5.4).

A trade of signed size q shifts the price by a permanent component (gamma*q,
stays) plus a temporary component (eta*q, decays toward zero over time). The
observed transaction price is mid + permanent + temporary; the mid itself only
absorbs the permanent part.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LinearImpactModel:
    gamma: float = 1e-6          # permanent impact per share
    eta: float = 1e-5            # temporary impact per share
    decay: float = 0.5          # fraction of temporary impact surviving each step
    mid0: float = 100.0
    _perm: float = field(default=0.0, init=False)
    _temp: float = field(default=0.0, init=False)

    def trade(self, signed_qty: float) -> float:
        """Apply a trade; return the execution price (incl. temporary impact)."""
        self._perm += self.gamma * signed_qty
        self._temp += self.eta * signed_qty
        return self.price()

    def price(self) -> float:
        return self.mid0 + self._perm + self._temp

    def mid(self) -> float:
        return self.mid0 + self._perm        # permanent component only

    def step(self) -> None:
        self._temp *= self.decay             # temporary impact decays
