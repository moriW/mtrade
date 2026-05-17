import pytest
import pandas as pd
from datetime import date
from unittest.mock import patch
from qtrade.data.collectors.akshare_provider import AkShareProvider
from qtrade.data.storage.parquet_storage import ParquetStorage
from qtrade.data.validators.quality import QualityValidator
from qtrade.data.schema import DailyBarSchema


@patch("qtrade.data.collectors.akshare_provider.ak.tool_trade_date_hist_sina")
def test_akshare_provider_calendar(mock_tool):
    mock_df = pd.DataFrame({"trade_date": ["2023-01-04", "2023-01-05"]})
    mock_tool.return_value = mock_df
    
    provider = AkShareProvider()
    start = date(2023, 1, 1)
    end = date(2023, 1, 10)
    df = provider.get_trade_calendar(start, end)
    
    assert not df.empty
    assert "trade_date" in df.columns
    assert "is_open" in df.columns
    assert "version" in df.columns
    assert len(df) == 10


def test_parquet_storage_and_quality(tmp_path):
    storage = ParquetStorage(base_dir=str(tmp_path))
    
    data = {
        "trade_date": [date(2023, 1, 4), date(2023, 1, 5)],
        "symbol": ["000001.SZ", "000001.SZ"],
        "open": [10.0, 10.2],
        "high": [10.5, 10.6],
        "low": [9.8, 10.0],
        "close": [10.2, 10.5],
        "volume": [100000.0, 150000.0],
        "amount": [1000000.0, 1500000.0],
        "source": ["akshare", "akshare"],
        "as_of_date": [date(2023, 1, 5), date(2023, 1, 5)],
        "ingested_at": [pd.Timestamp.now(), pd.Timestamp.now()],
        "version": ["v1", "v1"]
    }
    df = pd.DataFrame(data)
    
    validator = QualityValidator(df, "daily_bar")
    report = validator.generate_report()
    assert report["total_rows"] == 2
    assert report["duplicates"] == 0
    assert report["anomalies"]["price_anomaly"] == 0
    
    storage.save(df, "daily_bar", schema=DailyBarSchema, partition_cols=["symbol"])
    
    loaded_df = storage.load("daily_bar")
    assert not loaded_df.empty
    assert len(loaded_df) == 2
    assert loaded_df["symbol"].iloc[0] == "000001.SZ"
