import numpy as np

from execution.schedules import twap_schedule, u_shaped_profile, vwap_schedule


def test_twap_equal_and_sums():
    s = twap_schedule(1000, 10)
    assert len(s) == 10
    assert np.allclose(s, 100)
    assert abs(s.sum() - 1000) < 1e-9


def test_vwap_sums_and_is_u_shaped():
    s = vwap_schedule(1000, u_shaped_profile(11))
    assert abs(s.sum() - 1000) < 1e-9
    assert s[0] > s[len(s) // 2]            # heavier at the open than the middle
    assert s[-1] > s[len(s) // 2]
