from execution.order_book import LimitOrderBook


def test_best_bid_ask_mid_spread():
    b = LimitOrderBook()
    b.add_limit("buy", 99, 10)
    b.add_limit("buy", 98, 5)
    b.add_limit("sell", 101, 8)
    b.add_limit("sell", 102, 4)
    assert b.best_bid() == 99
    assert b.best_ask() == 101
    assert b.mid() == 100
    assert b.spread() == 2


def test_market_order_walks_levels_at_worsening_prices():
    b = LimitOrderBook()
    b.add_limit("sell", 101, 5)
    b.add_limit("sell", 102, 5)
    b.add_limit("sell", 103, 5)
    fills = b.market_order("buy", 12)              # 5@101, 5@102, 2@103
    assert [(f.price, f.qty) for f in fills] == [(101, 5), (102, 5), (103, 2)]
    assert b.best_ask() == 103
    assert b.depth("sell", 1) == [(103, 3)]


def test_cancel_removes_liquidity():
    b = LimitOrderBook()
    oid, _ = b.add_limit("buy", 99, 10)
    b.add_limit("buy", 98, 5)
    assert b.best_bid() == 99
    assert b.cancel(oid) is True
    assert b.best_bid() == 98                      # whole level gone
    assert b.cancel(oid) is False                  # already cancelled


def test_marketable_limit_crosses_then_rests():
    b = LimitOrderBook()
    b.add_limit("sell", 101, 5)
    _oid, fills = b.add_limit("buy", 101, 8)       # buy 5@101, rest 3 as a bid
    assert sum(f.qty for f in fills) == 5
    assert b.best_bid() == 101
    assert b.best_ask() is None
    assert b.depth("buy", 1) == [(101, 3)]


def test_cancelled_order_skipped_in_matching():
    b = LimitOrderBook()
    o1, _ = b.add_limit("sell", 101, 5)
    o2, _ = b.add_limit("sell", 101, 5)            # same level, behind o1
    b.cancel(o1)
    fills = b.market_order("buy", 5)               # must skip the tombstone o1
    assert sum(f.qty for f in fills) == 5
    assert all(f.resting_id == o2 for f in fills)
    assert b.best_ask() is None
