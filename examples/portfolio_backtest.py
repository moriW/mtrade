from datetime import date
import pandas as pd
import numpy as np

from qtrade.strategy.portfolio import PortfolioBuilder
from qtrade.backtest.cost import CostModel, SlippageModel
from qtrade.backtest.daily_engine import DailyBacktestEngine
from qtrade.report.performance import PerformanceAnalyzer
from qtrade.core.log import setup_logging

def main():
    setup_logging(level="INFO")
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
    
    # 模拟在每个月末生成目标权重（月频调仓）
    print("Generating target weights (monthly rebalance)...")
    rebalance_dates = pd.date_range("2023-01-01", "2023-12-31", freq="ME").date
    weight_data = []
    
    for rd in rebalance_dates:
        # 每月末随机给个打分
        for s in symbols:
            weight_data.append({
                "trade_date": rd,
                "symbol": s,
                "score": np.random.uniform()
            })
            
    scores_df = pd.DataFrame(weight_data).set_index(["trade_date", "symbol"])["score"]
    
    # 构建权重
    target_weights = PortfolioBuilder.generate_target_weights(
        scores_df, 
        top_n=2, 
        weight_method="equal", 
        max_weight=0.5
    )
    
    print(f"Target weights generated for {len(rebalance_dates)} periods.")

    # 运行回测
    print("\nRunning daily backtest engine...")
    cost = CostModel(commission_rate=0.0003, min_commission=5.0, stamp_tax_rate=0.0005, transfer_fee_rate=0.00001)
    slip = SlippageModel(slippage_rate=0.001)
    
    engine = DailyBacktestEngine(bars, target_weights, initial_cash=1000000.0, cost_model=cost, slippage_model=slip)
    engine.run()
    
    print(f"Executed {len(engine.history_trades)} trades.")
    
    print("\nGenerating Performance Report...")
    analyzer = PerformanceAnalyzer(engine.history_equity, engine.history_trades)
    print(analyzer.generate_report())

if __name__ == "__main__":
    main()
