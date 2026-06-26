"""Almgren-Chriss optimal execution (Phase 5.5).

Liquidate X shares over horizon T in N steps (tau = T/N), trading off temporary
market impact (eta) against timing risk (sigma) under risk aversion lambda. The
curvature kappa controls the shape:

    eta_tilde = eta - 0.5 * gamma * tau
    kappa     = sqrt(lambda * sigma^2 / eta_tilde)
    x_j       = X * sinh(kappa (T - t_j)) / sinh(kappa T)      (holdings)

lambda -> 0  =>  kappa -> 0  =>  linear holdings  =>  uniform trades (TWAP-like).
lambda large =>  large kappa =>  holdings decay fast =>  trades front-loaded.
"""
from __future__ import annotations

import numpy as np


def ac_trajectory(X, T, N, sigma, eta, gamma=0.0, lam=1e-6):
    """Return (holdings x[0..N], trades n[0..N-1]) for selling X over N steps."""
    tau = T / N
    eta_tilde = eta - 0.5 * gamma * tau
    if eta_tilde <= 0:
        eta_tilde = eta
    kappa = np.sqrt(max(lam * sigma**2 / eta_tilde, 0.0))
    kappa = min(kappa, 20.0 / T)                 # keep sinh well-conditioned

    t = np.linspace(0.0, T, N + 1)
    if kappa < 1e-8:
        x = X * (1.0 - t / T)                    # risk-neutral limit: linear
    else:
        x = X * np.sinh(kappa * (T - t)) / np.sinh(kappa * T)
    x[0], x[-1] = X, 0.0
    trades = -np.diff(x)                          # shares sold each interval (>=0)
    return x, trades
