from backtest.data import DataHandler
from backtest.engine import Backtest
from backtest.execution import SimulatedExecutionHandler
from backtest.portfolio import Portfolio
from strategies import BuyAndHold, MACrossover


def _run(strategy_factory, bars):
    data = DataHandler({"TEST": bars}, ["TEST"])
    pf = Portfolio(data, ["TEST"], initial_capital=100_000.0)
    strat = strategy_factory(data)
    return Backtest(data, strat, pf, SimulatedExecutionHandler(data)).run()


def test_buy_and_hold_trades_once(make_bars):
    pf = _run(lambda d: BuyAndHold(d, ["TEST"]), make_bars(list(range(100, 120))))
    assert len(pf.trades) == 1
    assert pf.trades[0].direction == "BUY"


def test_ma_crossover_enters_and_exits(make_bars):
    # 30 bars up then 30 down -> at least one LONG and one EXIT
    closes = list(range(100, 130)) + list(range(128, 98, -1))
    pf = _run(lambda d: MACrossover(d, ["TEST"], short_window=5, long_window=20), make_bars(closes))
    assert len(pf.trades) >= 2
    assert pf.trades[0].direction == "BUY"
    assert any(t.direction == "SELL" for t in pf.trades)
