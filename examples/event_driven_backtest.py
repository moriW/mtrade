from datetime import date
import pandas as pd
import numpy as np

from qtrade.strategy.portfolio import PortfolioBuilder
from qtrade.backtest.daily_engine import DailyBacktestEngine
from qtrade.backtest.event_engine import EventDrivenBacktestEngine
from qtrade.backtest.comparison import compare_backtests
from qtrade.backtest.broker_sim import ExecutionMode
from qtrade.risk.engine import SingleStockWeightRule
from qtrade.report.performance import PerformanceAnalyzer
from qtrade.core.log import setup_logging


def main():
    setup_logging(level="WARNING")
    print("Generating mock market data...")
    dates = pd.date_range("2023-01-01", "2023-12-31").date
    symbols = ["000001.SZ", "000002.SZ", "600000.SH"]

    data = []
    np.random.seed(42)
    for s in symbols:
        price = 10.0
        for d in dates:
            ret = np.random.normal(0.0005, 0.02)
            price = price * (1 + ret)
            data.append({
                "trade_date": d,
                "symbol": s,
                "open": price,
                "close": price,
            })
    bars = pd.DataFrame(data)

    print("Generating target weights (monthly rebalance)...")
    rebalance_dates = pd.date_range("2023-01-01", "2023-12-31", freq="ME").date
    weight_data = []
    for rd in rebalance_dates:
        for s in symbols:
            weight_data.append({
                "trade_date": rd,
                "symbol": s,
                "score": np.random.uniform()
            })
    scores_df = pd.DataFrame(weight_data).set_index(["trade_date", "symbol"])["score"]
    target_weights = PortfolioBuilder.generate_target_weights(
        scores_df, top_n=2, weight_method="equal", max_weight=0.5
    )

    print("\n--- O3 Daily Engine ---")
    o3_engine = DailyBacktestEngine(bars, target_weights, initial_cash=1000000.0)
    o3_engine.run()
    o3_analyzer = PerformanceAnalyzer(o3_engine.history_equity, o3_engine.history_trades)
    print(o3_analyzer.generate_report())

    print("\n--- O4 Event-Driven Engine ---")
    o4_engine = EventDrivenBacktestEngine(
        bars, target_weights,
        initial_cash=1000000.0,
        execution_mode=ExecutionMode.OPEN,
        risk_rules=[SingleStockWeightRule(max_weight=0.5)],
    )
    o4_engine.run()
    print(o4_engine.generate_report())

    print("\n--- O3 vs O4 Comparison ---")
    comparison = compare_backtests(
        o3_engine.history_equity, o3_engine.history_trades,
        o4_engine.history_equity, o4_engine.history_trades,
    )
    for k, v in comparison.items():
        if k == "explanations":
            print(f"  {k}:")
            for e in v:
                print(f"    - {e}")
        else:
            print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
