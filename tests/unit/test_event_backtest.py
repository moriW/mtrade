import pandas as pd
from datetime import date

from qtrade.backtest.events import EventBus, MarketDataEvent, OrderEvent, EventType
from qtrade.backtest.broker_sim import SimulatedBroker, OrderState
from qtrade.risk.engine import RiskEngine, SingleStockWeightRule, CashConstraintRule
from qtrade.backtest.event_engine import EventDrivenBacktestEngine
from qtrade.backtest.comparison import compare_backtests


def test_event_bus():
    bus = EventBus()
    bus.publish(
        MarketDataEvent(
            trade_date=date(2023, 1, 1),
            symbol="A",
            open=10.0,
            high=11.0,
            low=9.0,
            close=10.5,
            volume=1000.0,
            amount=10000.0,
        )
    )
    bus.publish(
        MarketDataEvent(
            trade_date=date(2023, 1, 1),
            symbol="B",
            open=20.0,
            high=21.0,
            low=19.0,
            close=20.5,
            volume=2000.0,
            amount=40000.0,
        )
    )
    assert bus.pending_count() == 2
    e = bus.next()
    assert e is not None
    assert bus.pending_count() == 1
    assert len(bus.get_history(EventType.MARKET_DATA)) == 2


def test_order_state_machine():
    assert OrderState.transition("new", "submitted")
    assert OrderState.transition("submitted", "filled")
    assert OrderState.transition("submitted", "partial")
    assert not OrderState.transition("filled", "canceled")
    assert not OrderState.transition("rejected", "submitted")


def test_risk_engine():
    engine = RiskEngine(
        rules=[
            SingleStockWeightRule(max_weight=1.0),
            CashConstraintRule(),
        ]
    )
    order = OrderEvent(
        trade_date=date(2023, 1, 1),
        symbol="A",
        direction="long",
        price=10.0,
        volume=600000,
    )
    account = {"cash": 5000.0, "total_value": 5000.0, "prices": {}}
    positions = {}
    results = engine.check_order(order, account, positions)
    assert not engine.is_approved(results)

    order2 = OrderEvent(
        trade_date=date(2023, 1, 1),
        symbol="A",
        direction="long",
        price=10.0,
        volume=100,
    )
    results2 = engine.check_order(order2, account, positions)
    assert engine.is_approved(results2)


def test_broker_sim_buy_and_sell():
    bus = EventBus()
    bars = {
        (date(2023, 1, 2), "A"): {
            "open": 10.0,
            "high": 12.0,
            "low": 9.0,
            "close": 11.0,
        },
        (date(2023, 1, 3), "A"): {
            "open": 12.0,
            "high": 14.0,
            "low": 11.0,
            "close": 13.0,
        },
    }
    broker = SimulatedBroker(bus, bars, initial_cash=100000.0)

    buy = OrderEvent(
        trade_date=date(2023, 1, 2),
        symbol="A",
        direction="long",
        price=10.0,
        volume=1000,
    )
    broker.submit_order(buy)
    broker.process_orders(date(2023, 1, 2))
    broker.end_of_day_settlement(date(2023, 1, 2))

    assert broker.positions.get("A", 0) > 0
    assert broker.available_volume.get("A", 0) > 0
    assert broker.locked_volume.get("A", 0) == 0
    assert len(broker.trades) == 1
    assert broker.trades[0].direction == "long"

    sell = OrderEvent(
        trade_date=date(2023, 1, 3),
        symbol="A",
        direction="short",
        price=12.0,
        volume=1000,
    )
    broker.submit_order(sell)
    broker.process_orders(date(2023, 1, 3))
    broker.end_of_day_settlement(date(2023, 1, 3))

    assert len(broker.trades) == 2
    assert broker.trades[1].direction == "short"


def test_event_driven_engine_execution():
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
    target_weights = pd.Series([0.5], index=idx)

    engine = EventDrivenBacktestEngine(
        bars,
        target_weights,
        initial_cash=10000.0,
        risk_rules=[SingleStockWeightRule(max_weight=1.0), CashConstraintRule()],
    )
    engine.run()

    assert len(engine.history_trades) == 1
    assert engine.history_trades[0]["direction"] == "long"


def test_comparison_tool():
    o3_equity = [
        {"trade_date": date(2023, 1, 1), "equity": 100000.0},
        {"trade_date": date(2023, 1, 2), "equity": 105000.0},
    ]
    o4_equity = [
        {"trade_date": date(2023, 1, 1), "equity": 100000.0},
        {"trade_date": date(2023, 1, 2), "equity": 104800.0},
    ]
    o3_trades = [{"symbol": "A", "volume": 100}]
    o4_trades = [{"symbol": "A", "volume": 90}]

    result = compare_backtests(o3_equity, o3_trades, o4_equity, o4_trades)
    assert abs(result["final_diff_pct"]) > 0.01
    assert result["o3_trades"] == result["o4_trades"]
