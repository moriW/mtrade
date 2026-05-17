import pandas as pd
import numpy as np


class PerformanceAnalyzer:
    def __init__(self, history_equity: list, history_trades: list, risk_free_rate: float = 0.02):
        self.history_equity = history_equity
        self.history_trades = history_trades
        self.risk_free_rate = risk_free_rate
        
        self.equity_df = pd.DataFrame(self.history_equity)
        if not self.equity_df.empty:
            self.equity_df["trade_date"] = pd.to_datetime(self.equity_df["trade_date"])
            self.equity_df.set_index("trade_date", inplace=True)
            self.equity_df["returns"] = self.equity_df["equity"].pct_change().fillna(0.0)
            
        self.trades_df = pd.DataFrame(self.history_trades)

    def compute_metrics(self) -> dict:
        if self.equity_df.empty:
            return {}

        total_return = (self.equity_df["equity"].iloc[-1] / self.equity_df["equity"].iloc[0]) - 1
        
        days = (self.equity_df.index[-1] - self.equity_df.index[0]).days
        years = max(days / 365.25, 1e-5)
        annualized_return = (1 + total_return) ** (1 / years) - 1
        
        daily_volatility = self.equity_df["returns"].std()
        annualized_volatility = daily_volatility * np.sqrt(252)
        
        if annualized_volatility > 0:
            sharpe_ratio = (annualized_return - self.risk_free_rate) / annualized_volatility
        else:
            sharpe_ratio = 0.0

        cum_max = self.equity_df["equity"].cummax()
        drawdowns = (cum_max - self.equity_df["equity"]) / cum_max
        max_drawdown = drawdowns.max()

        if not self.trades_df.empty:
            trade_val = (self.trades_df["volume"] * self.trades_df["price"]).sum()
            avg_equity = self.equity_df["equity"].mean()
            annualized_turnover = (trade_val / avg_equity) / years
        else:
            annualized_turnover = 0.0

        return {
            "total_return": total_return,
            "annualized_return": annualized_return,
            "annualized_volatility": annualized_volatility,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "annualized_turnover": annualized_turnover,
            "total_trades": len(self.trades_df)
        }

    def generate_report(self) -> str:
        metrics = self.compute_metrics()
        if not metrics:
            return "No performance data available."
            
        lines = [
            "=== Performance Report ===",
            f"Total Return:       {metrics['total_return'] * 100:.2f}%",
            f"Annualized Return:  {metrics['annualized_return'] * 100:.2f}%",
            f"Annual Volatility:  {metrics['annualized_volatility'] * 100:.2f}%",
            f"Max Drawdown:       {metrics['max_drawdown'] * 100:.2f}%",
            f"Sharpe Ratio:       {metrics['sharpe_ratio']:.2f}",
            f"Annual Turnover:    {metrics['annualized_turnover']:.2f}x",
            f"Total Trades:       {metrics['total_trades']}",
            "=========================="
        ]
        return "\n".join(lines)
