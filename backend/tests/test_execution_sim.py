"""The Phase 5 headline: Almgren-Chriss front-loading cuts timing risk (the std
of implementation shortfall) versus uniform TWAP."""
from execution.schedules import ac_schedule, twap_schedule
from execution.simulator import monte_carlo_is

SIM = dict(mid0=100.0, tick=0.05, sigma=0.0015, perm_impact=0.0,
           liquidity_per_level=1500, levels=40)


def test_ac_high_lambda_has_lower_risk_than_twap():
    X, N = 20_000, 12
    twap = twap_schedule(X, N)
    ac = ac_schedule(X, 1.0, N, sigma=0.02, eta=2e-6, lam=5e-2)

    r_twap = monte_carlo_is(twap, "buy", n_paths=80, base_seed=0, **SIM)
    r_ac = monte_carlo_is(ac, "buy", n_paths=80, base_seed=0, **SIM)

    assert r_ac["std_is_bps"] < r_twap["std_is_bps"]    # front-loading cuts risk
    assert r_twap["mean_is_bps"] > 0                     # buying into the book costs
