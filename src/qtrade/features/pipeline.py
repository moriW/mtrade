import pandas as pd


class FactorPipeline:
    """因子清洗流水线：去极值、标准化、缺失值填充"""

    @staticmethod
    def winsorize(series: pd.Series, method: str = "mad", n: float = 3.0) -> pd.Series:
        if method == "mad":
            median = series.median()
            mad = (series - median).abs().median()
            upper = median + n * mad
            lower = median - n * mad
            return series.clip(lower, upper)
        elif method == "quantile":
            lower = series.quantile(0.025)
            upper = series.quantile(0.975)
            return series.clip(lower, upper)
        return series

    @staticmethod
    def standardize(series: pd.Series) -> pd.Series:
        std = series.std()
        if std == 0 or pd.isna(std):
            return series - series.mean()
        return (series - series.mean()) / std

    @staticmethod
    def fill_na(series: pd.Series, value: float = 0.0) -> pd.Series:
        return series.fillna(value)

    @classmethod
    def process_cross_section(
        cls,
        cross_section: pd.Series,
        do_winsorize: bool = True,
        do_standardize: bool = True,
        fill_na_val: float = 0.0,
    ) -> pd.Series:
        """对横截面数据进行标准清洗"""
        s = cross_section.copy()

        if do_winsorize:
            s = cls.winsorize(s)

        if do_standardize:
            s = cls.standardize(s)

        s = cls.fill_na(s, fill_na_val)
        return s

    @classmethod
    def process_panel(cls, panel: pd.Series) -> pd.Series:
        if "trade_date" not in panel.index.names:
            raise ValueError("Index must contain 'trade_date'")

        return panel.groupby("trade_date", group_keys=False).apply(
            cls.process_cross_section
        )
