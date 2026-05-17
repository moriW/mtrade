import pandas as pd
import numpy as np
from typing import Dict, Any


class FactorEvaluator:
    """因子评价体系"""

    @staticmethod
    def calculate_forward_returns(bars: pd.DataFrame, periods: int = 1) -> pd.Series:
        """
        计算未来 N 期的收益率作为标签。
        未来收益对齐到当期：即 T 日的标签是 T+1 到 T+N+1 的收益。
        """
        close = bars.pivot(index="trade_date", columns="symbol", values="close")
        fwd_ret = close.pct_change(periods=periods).shift(-periods)
        
        return fwd_ret.unstack().reorder_levels(["symbol", "trade_date"]).dropna()

    @staticmethod
    def calc_ic(factor_panel: pd.Series, fwd_returns: pd.Series, method: str = "pearson") -> pd.DataFrame:
        df = pd.concat([factor_panel.rename("factor"), fwd_returns.rename("fwd_ret")], axis=1).dropna()
        if df.empty:
            return pd.DataFrame()
            
        ic_series = df.groupby("trade_date").apply(
            lambda x: x["factor"].corr(x["fwd_ret"], method=method)
        )
        return ic_series.to_frame(name="ic")

    @staticmethod
    def calc_quantiles(factor_panel: pd.Series, quantiles: int = 5) -> pd.Series:
        """
        按横截面划分因子分位数
        """
        def _qcut(x):
            if len(x) < quantiles:
                return pd.Series(index=x.index, dtype=float)
            return pd.qcut(x, quantiles, labels=False, duplicates="drop") + 1
            
        return factor_panel.groupby("trade_date", group_keys=False).apply(_qcut)

    @staticmethod
    def calc_quantile_returns(quantiles_panel: pd.Series, fwd_returns: pd.Series) -> pd.DataFrame:
        """
        计算分层收益
        """
        df = pd.concat([quantiles_panel.rename("quantile"), fwd_returns.rename("fwd_ret")], axis=1).dropna()
        if df.empty:
            return pd.DataFrame()
            
        q_ret = df.groupby(["trade_date", "quantile"])["fwd_ret"].mean().unstack("quantile")
        return q_ret

    @classmethod
    def generate_report(cls, factor_panel: pd.Series, bars: pd.DataFrame, horizon: int = 1) -> Dict[str, Any]:
        fwd_ret = cls.calculate_forward_returns(bars, periods=horizon)
        
        common_idx = factor_panel.index.intersection(fwd_ret.index)
        if len(common_idx) == 0:
            return {"error": "No overlapping dates between factor and forward returns."}
            
        aligned_factor = factor_panel.loc[common_idx]
        aligned_fwd_ret = fwd_ret.loc[common_idx]
        
        ic_df = cls.calc_ic(aligned_factor, aligned_fwd_ret, method="pearson")
        rank_ic_df = cls.calc_ic(aligned_factor, aligned_fwd_ret, method="spearman")
        
        quantiles = cls.calc_quantiles(aligned_factor, 5)
        q_returns = cls.calc_quantile_returns(quantiles, aligned_fwd_ret)
        
        report = {
            "ic_mean": ic_df["ic"].mean() if not ic_df.empty else 0.0,
            "ic_ir": (ic_df["ic"].mean() / ic_df["ic"].std()) if not ic_df.empty and ic_df["ic"].std() != 0 else 0.0,
            "rank_ic_mean": rank_ic_df["ic"].mean() if not rank_ic_df.empty else 0.0,
            "rank_ic_ir": (rank_ic_df["ic"].mean() / rank_ic_df["ic"].std()) if not rank_ic_df.empty and rank_ic_df["ic"].std() != 0 else 0.0,
            "coverage": len(common_idx) / len(factor_panel) if len(factor_panel) > 0 else 0.0,
            "quantile_returns_mean": q_returns.mean().to_dict() if not q_returns.empty else {}
        }
        
        return report
