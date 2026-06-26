"""Execution schedules (Phase 5.6): TWAP, VWAP, and Almgren-Chriss slices.

Each returns an array of child-order sizes summing to X over N intervals.
"""
from __future__ import annotations

import numpy as np

from execution.almgren_chriss import ac_trajectory


def twap_schedule(X: float, N: int) -> np.ndarray:
    """Equal slices."""
    return np.full(N, X / N)


def u_shaped_profile(N: int) -> np.ndarray:
    """A simple U-shaped intraday volume profile (heavier at open/close)."""
    t = np.linspace(0.0, 1.0, N)
    return 1.0 + 1.5 * (2.0 * (t - 0.5)) ** 2


def vwap_schedule(X: float, volume_profile) -> np.ndarray:
    """Slices proportional to a volume profile."""
    p = np.asarray(volume_profile, dtype=float)
    p = p / p.sum()
    return X * p


def ac_schedule(X, T, N, sigma, eta, gamma=0.0, lam=1e-6) -> np.ndarray:
    """Almgren-Chriss trade sizes."""
    _x, trades = ac_trajectory(X, T, N, sigma, eta, gamma, lam)
    return trades
