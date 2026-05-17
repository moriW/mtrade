import pytest
import pandas as pd
import numpy as np
from datetime import date

from qtrade.research.universe import UniverseFilter
from qtrade.features.factors.base import MomentumFactor, SizeFactor
from qtrade.features.pipeline import FactorPipeline
from qtrade.research.evaluation import FactorEvaluator


@pytest.fixture
def sample_data():
    dates = pd.date_range("2023-01-01", "2023-01-10").date
    symbols = ["000001.SZ", "000002.SZ"]
    
    bars_data = []
    for d in dates:
        for s in symbols:
            bars_data.append({
                "trade_date": d,
                "symbol": s,
                "close": np.random.uniform(10, 20),
                "volume": np.random.uniform(1000, 5000),
                "amount": np.random.uniform(10000, 50000)
            })
    bars = pd.DataFrame(bars_data)
    
    master = pd.DataFrame({
        "symbol": symbols,
        "list_date": [date(2020, 1, 1), date(2021, 1, 1)],
        "delist_date": [None, None],
        "is_st": [False, True]
    })
    
    suspensions = pd.DataFrame({
        "trade_date": [date(2023, 1, 5)],
        "symbol": ["000001.SZ"],
        "is_suspended": [True]
    })
    
    return bars, master, suspensions


def test_universe_filter(sample_data):
    bars, master, suspensions = sample_data
    uf = UniverseFilter(master, bars, suspensions)
    
    symbols = uf.filter(date(2023, 1, 5), min_list_days=30, exclude_st=True, exclude_suspended=True)
    assert len(symbols) == 0

    symbols_no_susp = uf.filter(date(2023, 1, 4), min_list_days=30, exclude_st=True, exclude_suspended=True)
    assert symbols_no_susp == ["000001.SZ"]


def test_factor_computation(sample_data):
    bars, _, _ = sample_data
    mom = MomentumFactor(window=2)
    mom_val = mom.compute(bars)
    assert not mom_val.empty
    assert mom_val.index.names == ["symbol", "trade_date"]
    
    size = SizeFactor()
    size_val = size.compute(bars)
    assert not size_val.empty


def test_pipeline_processing():
    idx = pd.MultiIndex.from_product(
        [["000001.SZ", "000002.SZ", "000003.SZ"], pd.date_range("2023-01-01", "2023-01-02")],
        names=["symbol", "trade_date"]
    )
    s = pd.Series([1.0, 1.0, 100.0, -100.0, 2.0, 2.0], index=idx)
    
    processed = FactorPipeline.process_panel(s)
    
    assert not processed.isna().any()
    assert processed.max() < 50.0
    assert processed.min() > -50.0


def test_evaluation(sample_data):
    bars, _, _ = sample_data
    size = SizeFactor()
    size_val = size.compute(bars)
    
    report = FactorEvaluator.generate_report(size_val, bars, horizon=1)
    
    assert "ic_mean" in report
    assert "rank_ic_mean" in report
    assert "quantile_returns_mean" in report
