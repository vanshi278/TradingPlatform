from execution.impact import LinearImpactModel


def test_buy_moves_price_up_with_permanent_and_temporary():
    m = LinearImpactModel(gamma=1e-3, eta=1e-2, decay=0.5, mid0=100.0)
    price = m.trade(100)                  # buy 100 shares
    assert price > 100.0
    assert m.mid() > 100.0                # permanent component moved the mid
    assert m.price() > m.mid()            # temporary impact sits on top


def test_temporary_impact_decays_toward_mid():
    m = LinearImpactModel(gamma=0.0, eta=1e-2, decay=0.5, mid0=100.0)
    m.trade(100)
    before = m.price()
    m.step()
    after = m.price()
    assert 100.0 < after < before         # decayed, but not instantly
    assert m.mid() == 100.0               # no permanent impact (gamma=0)
