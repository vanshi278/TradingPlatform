import numpy as np

from execution.almgren_chriss import ac_trajectory


def test_low_lambda_is_uniform():
    _x, trades = ac_trajectory(X=1000, T=1.0, N=10, sigma=0.02, eta=2e-6, lam=1e-9)
    assert np.allclose(trades, 1000 / 10, rtol=0.02)     # ≈ uniform (TWAP-like)
    assert abs(trades.sum() - 1000) < 1e-6


def test_high_lambda_front_loads():
    x, trades = ac_trajectory(1000, 1.0, 10, sigma=0.02, eta=2e-6, lam=5e-2)
    assert trades[0] > trades[-1]                        # front-loaded
    assert abs(trades.sum() - 1000) < 1e-6
    assert np.all(np.diff(x) <= 1e-9)                    # holdings only decrease


def test_holdings_endpoints():
    x, _ = ac_trajectory(1000, 1.0, 10, sigma=0.02, eta=2e-6, lam=1e-2)
    assert x[0] == 1000 and abs(x[-1]) < 1e-9
