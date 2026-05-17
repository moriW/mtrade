import pandas as pd
from datetime import date

from qtrade.strategy.portfolio import PortfolioBuilder
from qtrade.backtest.cost import CostModel, SlippageModel
from qtrade.core.types import OrderDirection
from qtrade.backtest.daily_engine import DailyBacktestEngine
from qtrade.report.performance import PerformanceAnalyzer


def test_portfolio_builder():
    idx = pd.MultiIndex.from_product(
        [[date(2023, 1, 1)], ["000001.SZ", "000002.SZ", "000003.SZ"]],
        names=["trade_date", "symbol"],
    )
    scores = pd.Series([10.0, 5.0, 1.0], index=idx)

    weights = PortfolioBuilder.generate_target_weights(
        scores, top_n=2, weight_method="equal"
    )
    assert "000001.SZ" in weights[date(2023, 1, 1)].index
    assert "000002.SZ" in weights[date(2023, 1, 1)].index
    assert "000003.SZ" not in weights[date(2023, 1, 1)].index
    assert weights.loc[(date(2023, 1, 1), "000001.SZ")] == 0.5


def test_cost_and_slippage():
    cost_model = CostModel(
        commission_rate=0.001,
        min_commission=5.0,
        stamp_tax_rate=0.001,
        transfer_fee_rate=0.0,
    )

    buy_cost = cost_model.calculate(100, 10.0, OrderDirection.LONG)
    assert buy_cost["commission"] == 5.0
    assert buy_cost["tax"] == 0.0

    sell_cost = cost_model.calculate(1000, 10.0, OrderDirection.SHORT)
    assert sell_cost["commission"] == 10.0
    assert sell_cost["tax"] == 10.0

    slippage_model = SlippageModel(slippage_rate=0.01)
    assert slippage_model.calculate_price(10.0, OrderDirection.LONG) == 10.1
    assert slippage_model.calculate_price(10.0, OrderDirection.SHORT) == 9.9


def test_daily_engine_execution():
    dates = [
        pd.to_datetime("2023-01-01"),
        pd.to_datetime("2023-01-02"),
        pd.to_datetime("2023-01-03"),
    ]
    bars = pd.DataFrame(
        [
            {"trade_date": dates[0], "symbol": "A", "open": 10.0, "close": 10.0},
            {"trade_date": dates[1], "symbol": "A", "open": 10.0, "close": 12.0},
            {"trade_date": dates[2], "symbol": "A", "open": 12.0, "close": 15.0},
        ]
    )

    idx = pd.MultiIndex.from_product(
        [[dates[0]], ["A"]], names=["trade_date", "symbol"]
    )
    target_weights = pd.Series([1.0], index=idx)

    engine = DailyBacktestEngine(bars, target_weights, initial_cash=10000.0)
    engine.run()

    if len(engine.history_trades) != 1:
        print("REBALANCE DICT:", engine.target_weights)
        print("CASH:", engine.cash)

    assert len(engine.history_trades) == 1
    assert engine.history_trades[0]["volume"] == 900.0

    analyzer = PerformanceAnalyzer(engine.history_equity, engine.history_trades)
    metrics = analyzer.compute_metrics()

    assert metrics["total_return"] > 0
    assert metrics["total_trades"] == 1
