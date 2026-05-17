import pandas as pd
from typing import Optional


class PortfolioBuilder:
    """组合构建器：将因子打分转换为目标权重"""

    @staticmethod
    def generate_target_weights(
        scores_panel: pd.Series,
        top_n: int = 10,
        weight_method: str = "equal",
        max_weight: Optional[float] = None,
    ) -> pd.Series:
        """
        根据因子打分生成每一期的目标权重。
        scores_panel: MultiIndex [trade_date, symbol] 的因子得分
        """

        def _build_weights(scores: pd.Series) -> pd.Series:
            selected = scores.nlargest(top_n)
            if len(selected) == 0:
                return pd.Series(dtype=float)

            if weight_method == "equal":
                weights = pd.Series(1.0 / len(selected), index=selected.index)
            elif weight_method == "score":
                min_score = selected.min()
                if min_score < 0:
                    selected = selected - min_score + 1e-5
                weights = selected / selected.sum()
            else:
                raise ValueError(f"Unsupported weight method: {weight_method}")

            if max_weight is not None and max_weight > 0:
                weights = weights.clip(upper=max_weight)

            return weights

        target_weights = scores_panel.groupby("trade_date", group_keys=False).apply(
            _build_weights
        )
        return target_weights
