from abc import ABC, abstractmethod
import pandas as pd
from datetime import date


class DataProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def get_trade_calendar(self, start_date: date, end_date: date) -> pd.DataFrame:
        pass

    @abstractmethod
    def get_security_master(self) -> pd.DataFrame:
        pass

    @abstractmethod
    def get_daily_bars(
        self, symbol: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        pass

    @abstractmethod
    def get_adjust_factors(
        self, symbol: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        pass

    @abstractmethod
    def get_limit_prices(
        self, symbol: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        pass

    @abstractmethod
    def get_suspension_info(
        self, symbol: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        pass
