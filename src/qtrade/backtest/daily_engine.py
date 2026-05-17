import pandas as pd
from typing import Dict, Optional
from datetime import date
import uuid

from qtrade.core.types import OrderDirection
from qtrade.backtest.cost import CostModel, SlippageModel
from qtrade.core.log import get_logger

logger = get_logger("daily_engine")


class DailyBacktestEngine:
    def __init__(
        self,
        bars: pd.DataFrame,
        target_weights: pd.Series,
        initial_cash: float = 1000000.0,
        cost_model: Optional[CostModel] = None,
        slippage_model: Optional[SlippageModel] = None,
    ):
        self.bars = bars
        self.target_weights = target_weights
        self.cash = initial_cash
        self.positions: Dict[str, float] = {}

        self.cost_model = cost_model or CostModel()
        self.slippage_model = slippage_model or SlippageModel()

        self.history_equity = []
        self.history_trades = []

    def run(self):
        trade_dates = sorted(self.bars["trade_date"].unique())
        if len(trade_dates) == 0:
            return

        rebalance_dict = {}
        dates_with_signals = (
            self.target_weights.index.get_level_values("trade_date")
            .unique()
            .sort_values()
        )

        for d in dates_with_signals:
            next_dates = [td for td in trade_dates if td > d]
            if next_dates:
                next_d = next_dates[0]
                rebalance_dict[next_d] = self.target_weights.loc[d]

        bars_indexed = self.bars.set_index(["trade_date", "symbol"])

        for t_date in trade_dates:
            try:
                day_bars = bars_indexed.loc[t_date]
                if isinstance(day_bars, pd.Series):
                    day_bars = day_bars.to_frame().T
            except KeyError:
                day_bars = pd.DataFrame()

            current_value = self.cash
            prices_for_val = {}

            for sym, vol in self.positions.items():
                if vol > 0:
                    if sym in day_bars.index:
                        p = day_bars.loc[sym, "close"]
                    else:
                        p = 0.0
                    prices_for_val[sym] = p
                    current_value += vol * p

            if t_date in rebalance_dict:
                target_w = rebalance_dict[t_date]
                self._rebalance(t_date, target_w, day_bars, current_value)

                current_value = self.cash
                for sym, vol in self.positions.items():
                    if vol > 0 and sym in day_bars.index:
                        current_value += vol * day_bars.loc[sym, "close"]

            self.history_equity.append(
                {"trade_date": t_date, "equity": current_value, "cash": self.cash}
            )

    def _rebalance(
        self,
        t_date: date,
        target_w: pd.Series,
        day_bars: pd.DataFrame,
        current_value: float,
    ):
        if day_bars.empty:
            return

        target_positions = {}
        for sym, weight in target_w.items():
            if weight > 0:
                target_positions[sym] = current_value * weight

        sell_orders = []
        for sym, vol in self.positions.items():
            if vol > 0:
                target_val = target_positions.get(sym, 0.0)
                if sym not in day_bars.index:
                    continue
                bar = day_bars.loc[sym]

                if bar.get("is_suspended", False):
                    continue
                open_p = bar["open"]
                limit_down = bar.get("limit_down", 0.0)
                if open_p <= limit_down + 1e-5:
                    continue

                current_val = vol * open_p
                if current_val > target_val:
                    sell_val = current_val - target_val
                    sell_vol = sell_val / open_p
                    sell_orders.append((sym, sell_vol, open_p))

        for sym, vol, p in sell_orders:
            exec_p = self.slippage_model.calculate_price(p, OrderDirection.SHORT)
            cost = self.cost_model.calculate(vol, exec_p, OrderDirection.SHORT)

            self.cash += (vol * exec_p) - cost["total"]
            self.positions[sym] -= vol
            if self.positions[sym] <= 1e-5:
                self.positions[sym] = 0.0

            self._record_trade(t_date, sym, OrderDirection.SHORT, vol, exec_p, cost)

        buy_orders = []
        for sym, target_val in target_positions.items():
            if sym not in day_bars.index:
                continue
            bar = day_bars.loc[sym]

            if bar.get("is_suspended", False):
                continue
            open_p = bar["open"]
            limit_up = bar.get("limit_up", float("inf"))
            if open_p >= limit_up - 1e-5:
                continue

            curr_vol = self.positions.get(sym, 0.0)
            curr_val = curr_vol * open_p

            if target_val > curr_val:
                buy_val = target_val - curr_val
                buy_vol = (buy_val // (open_p * 100)) * 100
                if buy_vol >= 100:
                    buy_orders.append((sym, buy_vol, open_p))

        for sym, vol, p in buy_orders:
            exec_p = self.slippage_model.calculate_price(p, OrderDirection.LONG)
            cost = self.cost_model.calculate(vol, exec_p, OrderDirection.LONG)

            required_cash = (vol * exec_p) + cost["total"]
            if self.cash >= required_cash:
                self.cash -= required_cash
                self.positions[sym] = self.positions.get(sym, 0.0) + vol
                self._record_trade(t_date, sym, OrderDirection.LONG, vol, exec_p, cost)
            else:
                buy_val = self.cash - cost["total"]
                new_vol = (buy_val // (exec_p * 100)) * 100
                if new_vol >= 100:
                    new_cost = self.cost_model.calculate(
                        new_vol, exec_p, OrderDirection.LONG
                    )
                    new_req = (new_vol * exec_p) + new_cost["total"]
                    if self.cash >= new_req:
                        self.cash -= new_req
                        self.positions[sym] = self.positions.get(sym, 0.0) + new_vol
                        self._record_trade(
                            t_date, sym, OrderDirection.LONG, new_vol, exec_p, new_cost
                        )

    def _record_trade(self, t_date, sym, direction, vol, p, cost):
        self.history_trades.append(
            {
                "trade_id": str(uuid.uuid4()),
                "trade_date": t_date,
                "symbol": sym,
                "direction": direction,
                "price": p,
                "volume": vol,
                "commission": cost["commission"],
                "tax": cost["tax"],
                "transfer_fee": cost["transfer_fee"],
            }
        )
