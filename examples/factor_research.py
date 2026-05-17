from datetime import date
import pandas as pd
import numpy as np

from qtrade.features.factors.base import MomentumFactor, VolatilityFactor, LiquidityFactor, SizeFactor
from qtrade.features.pipeline import FactorPipeline
from qtrade.research.evaluation import FactorEvaluator

def main():
    print("Generating mock daily bars data...")
    dates = pd.date_range("2023-01-01", "2023-12-31").date
    symbols = ["000001.SZ", "000002.SZ", "600000.SH", "600036.SH", "000858.SZ"]
    
    data = []
    np.random.seed(42)
    for s in symbols:
        price = 10.0
        for d in dates:
            ret = np.random.normal(0.001, 0.02)
            price = price * (1 + ret)
            vol = np.random.uniform(10000, 50000)
            data.append({
                "trade_date": d,
                "symbol": s,
                "close": price,
                "volume": vol,
                "amount": price * vol
            })
            
    bars = pd.DataFrame(data)
    
    print("Computing Factors...")
    mom = MomentumFactor(window=20).compute(bars)
    volatility = VolatilityFactor(window=20).compute(bars)
    size = SizeFactor().compute(bars)
    
    print("\nProcessing Size Factor Pipeline (Winsorize -> Standardize)...")
    size_cleaned = FactorPipeline.process_panel(size)
    
    print("\nEvaluating Cleaned Size Factor...")
    report = FactorEvaluator.generate_report(size_cleaned, bars, horizon=5)
    
    print(f"IC Mean: {report['ic_mean']:.4f}")
    print(f"Rank IC Mean: {report['rank_ic_mean']:.4f}")
    print("Quantile Returns:")
    for quantile, qret in report['quantile_returns_mean'].items():
        print(f"  Q{int(quantile)}: {qret:.4f}")

if __name__ == "__main__":
    main()
