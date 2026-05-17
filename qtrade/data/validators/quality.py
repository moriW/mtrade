import pandas as pd
from typing import Dict, Any
from qtrade.core.log import get_logger

logger = get_logger("data_quality")


class QualityValidator:
    def __init__(self, df: pd.DataFrame, table_name: str):
        self.df = df
        self.table_name = table_name

    def generate_report(self) -> Dict[str, Any]:
        if self.df.empty:
            return {"status": "empty"}

        report = {
            "table_name": self.table_name,
            "total_rows": len(self.df),
            "missing_rates": self._check_missing(),
            "duplicates": self._check_duplicates(),
            "anomalies": {}
        }
        
        if self.table_name == "daily_bar":
            report["anomalies"]["price_anomaly"] = self._check_price_anomaly()
            
        logger.info("Quality report generated", table=self.table_name, report=report)
        return report

    def _check_missing(self) -> Dict[str, float]:
        missing = self.df.isna().mean().to_dict()
        return {k: round(v, 4) for k, v in missing.items()}

    def _check_duplicates(self) -> int:
        if "trade_date" in self.df.columns and "symbol" in self.df.columns:
            dups = self.df.duplicated(subset=["trade_date", "symbol"]).sum()
        elif "trade_date" in self.df.columns:
            dups = self.df.duplicated(subset=["trade_date"]).sum()
        elif "symbol" in self.df.columns:
            dups = self.df.duplicated(subset=["symbol"]).sum()
        else:
            dups = self.df.duplicated().sum()
        return int(dups)

    def _check_price_anomaly(self) -> int:
        if all(c in self.df.columns for c in ["open", "high", "low", "close"]):
            mask = (
                (self.df["low"] > self.df["high"]) |
                (self.df["open"] < 0) |
                (self.df["close"] < 0)
            )
            return int(mask.sum())
        return 0
