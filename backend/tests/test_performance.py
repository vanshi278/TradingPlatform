import pandas as pd
import pytest

from backtest.performance import compute_metrics, max_drawdown, sharpe_ratio


def test_max_drawdown():
    s = pd.Series([100, 120, 90, 150])
    # peak 120 -> trough 90 == -25%
    assert max_drawdown(s) == pytest.approx(-0.25)


def test_max_drawdown_monotonic_is_zero():
    assert max_drawdown(pd.Series([100, 101, 102, 103])) == pytest.approx(0.0)


def test_sharpe_zero_when_flat():
    assert sharpe_ratio(pd.Series([0.0, 0.0, 0.0])) == 0.0


def test_compute_metrics_on_rising_curve():
    idx = pd.date_range("2024-01-01", periods=5, freq="D", tz="UTC")
    df = pd.DataFrame({"total": [100.0, 101.0, 102.0, 103.0, 104.0]}, index=idx)
    m = compute_metrics(df, periods_per_year=252)
    assert m["total_return"] == pytest.approx(0.04)
    assert m["max_drawdown"] == pytest.approx(0.0)
    assert m["sharpe"] > 0
    assert m["n_periods"] == 5
