import pandas as pd
from typing import List, Optional
from datetime import date


class UniverseFilter:
    """股票池过滤机制"""

    def __init__(
        self,
        security_master: pd.DataFrame,
        daily_bars: pd.DataFrame,
        suspensions: pd.DataFrame,
    ):
        self.master = security_master
        self.bars = daily_bars
        self.suspensions = suspensions

    def filter(
        self,
        target_date: date,
        min_list_days: int = 60,
        exclude_st: bool = True,
        exclude_suspended: bool = True,
        min_volume: Optional[float] = None,
    ) -> List[str]:
        """
        根据指定条件过滤出目标日期的可用股票池
        """
        target_ts = pd.Timestamp(target_date)
        valid_master = self.master[
            (pd.to_datetime(self.master["list_date"]) <= target_ts)
            & (
                self.master["delist_date"].isna()
                | (pd.to_datetime(self.master["delist_date"]) > target_ts)
            )
        ]

        if min_list_days > 0:
            valid_master = valid_master[
                (target_ts - pd.to_datetime(valid_master["list_date"])).dt.days
                >= min_list_days
            ]

        if exclude_st:
            valid_master = valid_master[~valid_master["is_st"]]

        symbols = valid_master["symbol"].tolist()

        if exclude_suspended and not self.suspensions.empty:
            target_ts_dt = pd.to_datetime(target_date)
            susp = self.suspensions[
                pd.to_datetime(self.suspensions["trade_date"]) == target_ts_dt
            ]
            if not susp.empty:
                suspended_symbols = susp[susp["is_suspended"]]["symbol"].tolist()
                symbols = [s for s in symbols if s not in suspended_symbols]

        if min_volume is not None and min_volume > 0 and not self.bars.empty:
            target_ts_dt = pd.to_datetime(target_date)
            day_bars = self.bars[
                pd.to_datetime(self.bars["trade_date"]) == target_ts_dt
            ]
            if not day_bars.empty:
                liquid_symbols = day_bars[day_bars["volume"] >= min_volume][
                    "symbol"
                ].tolist()
                symbols = [s for s in symbols if s in liquid_symbols]

        return sorted(symbols)
