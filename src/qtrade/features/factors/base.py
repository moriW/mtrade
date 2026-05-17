import pandas as pd
import numpy as np


class BaseFactor:
    @property
    def name(self) -> str:
        raise NotImplementedError

    def compute(self, bars: pd.DataFrame) -> pd.Series:
        raise NotImplementedError


class MomentumFactor(BaseFactor):
    """
    动量因子：过去 N 日的累计收益率
    """

    def __init__(self, window: int = 20):
        self.window = window

    @property
    def name(self) -> str:
        return f"momentum_{self.window}"

    def compute(self, bars: pd.DataFrame) -> pd.Series:
        close = bars.pivot(index="trade_date", columns="symbol", values="close")
        returns = close.pct_change(periods=self.window)
        return returns.unstack().dropna()


class ReversalFactor(BaseFactor):
    """
    反转因子：过去 N 日的累计收益率的相反数
    """

    def __init__(self, window: int = 5):
        self.window = window

    @property
    def name(self) -> str:
        return f"reversal_{self.window}"

    def compute(self, bars: pd.DataFrame) -> pd.Series:
        close = bars.pivot(index="trade_date", columns="symbol", values="close")
        returns = close.pct_change(periods=self.window) * -1
        return returns.unstack().dropna()


class VolatilityFactor(BaseFactor):
    """
    波动率因子：过去 N 日收益率的标准差
    """

    def __init__(self, window: int = 20):
        self.window = window

    @property
    def name(self) -> str:
        return f"volatility_{self.window}"

    def compute(self, bars: pd.DataFrame) -> pd.Series:
        close = bars.pivot(index="trade_date", columns="symbol", values="close")
        daily_ret = close.pct_change(1)
        vol = daily_ret.rolling(window=self.window).std()
        return vol.unstack().dropna()


class LiquidityFactor(BaseFactor):
    """
    流动性因子：过去 N 日平均换手率 (此处用平均成交额简化替代，假设无流通股本数据)
    """

    def __init__(self, window: int = 20):
        self.window = window

    @property
    def name(self) -> str:
        return f"liquidity_amount_{self.window}"

    def compute(self, bars: pd.DataFrame) -> pd.Series:
        amount = bars.pivot(index="trade_date", columns="symbol", values="amount")
        avg_amount = amount.rolling(window=self.window).mean()
        return avg_amount.unstack().dropna()


class SizeFactor(BaseFactor):
    """
    市值因子：此处以 close * volume * (某一常数) 模拟市值，或者直接使用收盘价作为规模代理(演示用)
    (真实环境需要依赖总股本数据，此处用平均成交量*收盘价的对数模拟)
    """

    @property
    def name(self) -> str:
        return "size_proxy"

    def compute(self, bars: pd.DataFrame) -> pd.Series:
        proxy = np.log(bars["close"] * bars["volume"] + 1)
        res = pd.Series(proxy.values, index=[bars["symbol"], bars["trade_date"]])
        return res.dropna()
