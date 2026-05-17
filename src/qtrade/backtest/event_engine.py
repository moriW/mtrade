import pandas as pd
from typing import Dict, Optional
from datetime import date

from qtrade.backtest.events import MarketDataEvent, OrderEvent, EventBus, EventType
from qtrade.backtest.broker_sim import SimulatedBroker, ExecutionMode
from qtrade.backtest.cost import CostModel, SlippageModel
from qtrade.risk.engine import RiskEngine, RiskRule
from qtrade.report.performance import PerformanceAnalyzer
from qtrade.core.log import get_logger

logger = get_logger("event_engine")


class EventDrivenBacktestEngine:
    def __init__(
        self,
        bars: pd.DataFrame,
        target_weights: pd.Series,
        initial_cash: float = 1000000.0,
        execution_mode: ExecutionMode = ExecutionMode.OPEN,
        cost_model: Optional[CostModel] = None,
        slippage_model: Optional[SlippageModel] = None,
        risk_rules: Optional[list[RiskRule]] = None,
        lot_size: int = 100,
    ):
        self.bars = bars
        self.target_weights = target_weights
        self.initial_cash = initial_cash
        self.lot_size = lot_size

        self.event_bus = EventBus()

        bars_indexed = {}
        for _, row in bars.iterrows():
            key = (pd.Timestamp(row["trade_date"]).date(), row["symbol"])
            bars_indexed[key] = {
                "open": row["open"],
                "high": row.get("high", row["open"]),
                "low": row.get("low", row["open"]),
                "close": row["close"],
                "volume": row.get("volume", 0),
                "amount": row.get("amount", 0),
                "limit_up": row.get("limit_up"),
                "limit_down": row.get("limit_down"),
                "is_suspended": row.get("is_suspended", False),
            }

        self.broker = SimulatedBroker(
            event_bus=self.event_bus,
            bars=bars_indexed,
            initial_cash=initial_cash,
            execution_mode=execution_mode,
            cost_model=cost_model,
            slippage_model=slippage_model,
        )

        self.risk_engine = RiskEngine(rules=risk_rules)

        self.history_equity: list[dict] = []
        self.history_trades: list[dict] = []

    def run(self):
        trade_dates = sorted(self.bars["trade_date"].unique())
        if len(trade_dates) == 0:
            return

        rebalance_dict = self._map_rebalance_dates(trade_dates)
        prices_cache: Dict[str, float] = {}

        for t_date in trade_dates:
            t_date_dt = pd.Timestamp(t_date).date()
            day_bars = self.bars[self.bars["trade_date"] == t_date]

            self._publish_market_data(t_date_dt, day_bars)

            for _, row in day_bars.iterrows():
                prices_cache[row["symbol"]] = row["close"]

            if t_date in rebalance_dict:
                self._generate_signals_and_orders(
                    t_date_dt, rebalance_dict[t_date], day_bars, prices_cache
                )

            self.broker.process_orders(t_date_dt)
            self.broker.end_of_day_settlement(t_date_dt)

            account = self.broker.get_account_state(prices_cache)
            self.history_equity.append(
                {
                    "trade_date": t_date_dt,
                    "equity": account["total_value"],
                    "cash": account["cash"],
                }
            )

        self._collect_history_trades()

    def _map_rebalance_dates(self, trade_dates: list) -> dict:
        rebalance_dict = {}
        dates_with_signals = (
            self.target_weights.index.get_level_values("trade_date")
            .unique()
            .sort_values()
        )
        for d in dates_with_signals:
            next_dates = [td for td in trade_dates if td > d]
            if next_dates:
                rebalance_dict[next_dates[0]] = self.target_weights.loc[d]
        return rebalance_dict

    def _publish_market_data(self, t_date: date, day_bars: pd.DataFrame):
        for _, row in day_bars.iterrows():
            self.event_bus.publish(
                MarketDataEvent(
                    trade_date=t_date,
                    symbol=row["symbol"],
                    open=row["open"],
                    high=row.get("high", row["open"]),
                    low=row.get("low", row["open"]),
                    close=row["close"],
                    volume=row.get("volume", 0),
                    amount=row.get("amount", 0),
                    limit_up=row.get("limit_up"),
                    limit_down=row.get("limit_down"),
                    is_suspended=row.get("is_suspended", False),
                )
            )

    def _generate_signals_and_orders(
        self, t_date: date, target_w: pd.Series, day_bars: pd.DataFrame, prices: dict
    ):
        target_positions: Dict[str, float] = {}
        account = self.broker.get_account_state(prices)
        total_value = account["total_value"]

        for sym, weight in target_w.items():
            if weight > 0:
                target_positions[sym] = total_value * weight

        sell_orders = []
        for sym, vol in self.broker.positions.items():
            if vol <= 0 or sym not in prices:
                continue
            target_val = target_positions.get(sym, 0.0)
            current_val = vol * prices[sym]
            if current_val > target_val:
                sell_vol = (current_val - target_val) / prices.get(sym, 0)
                sell_orders.append((sym, sell_vol))

        for sym, vol in sell_orders:
            order = OrderEvent(
                trade_date=t_date,
                symbol=sym,
                direction="short",
                price=prices[sym],
                volume=vol,
            )
            self._submit_with_risk_check(order, account, prices)

        for sym, target_val in target_positions.items():
            bar_row = day_bars[day_bars["symbol"] == sym]
            if bar_row.empty:
                continue

            bar = bar_row.iloc[0]
            if bar.get("is_suspended", False):
                continue

            limit_up = bar.get("limit_up") or float("inf")
            if bar["open"] >= limit_up - 1e-5:
                continue

            curr_vol = self.broker.positions.get(sym, 0.0)
            curr_val = curr_vol * prices.get(sym, 0.0)

            if target_val > curr_val:
                buy_val = target_val - curr_val
                buy_vol = int(buy_val // (bar["open"] * self.lot_size)) * self.lot_size
                if buy_vol >= self.lot_size:
                    order = OrderEvent(
                        trade_date=t_date,
                        symbol=sym,
                        direction="long",
                        price=bar["open"],
                        volume=buy_vol,
                    )
                    self._submit_with_risk_check(order, account, prices)

    def _submit_with_risk_check(self, order: OrderEvent, account: dict, prices: dict):
        broker_positions = account.get("positions", {})
        results = self.risk_engine.check_order(order, account, broker_positions)
        if self.risk_engine.is_approved(results):
            self.broker.submit_order(order)
        else:
            failures = [r for r in results if not r.passed]
            logger.info(
                "Order blocked by risk", order_id=order.order_id, failures=failures
            )

    def _collect_history_trades(self):
        for trade in self.broker.trades:
            self.history_trades.append(
                {
                    "trade_id": trade.trade_id,
                    "order_id": trade.order_id,
                    "trade_date": trade.trade_date,
                    "symbol": trade.symbol,
                    "direction": trade.direction,
                    "price": trade.price,
                    "volume": trade.volume,
                    "commission": trade.commission,
                    "tax": trade.tax,
                    "transfer_fee": trade.transfer_fee,
                }
            )

    def generate_report(self) -> str:
        analyzer = PerformanceAnalyzer(self.history_equity, self.history_trades)
        base_report = analyzer.generate_report()

        order_events = self.event_bus.get_history(EventType.ORDER)
        trade_events = self.event_bus.get_history(EventType.TRADE)
        risk_events = self.event_bus.get_history(EventType.RISK)
        failed_risks = [r for r in risk_events if not r.passed]

        order_states = {}
        for e in order_events:
            order_states[e.order_id] = e.status

        lines = [
            base_report,
            "",
            "=== Event-Driven Detail ===",
            f"Total Orders:        {len(order_events)}",
            f"Total Trades:        {len(trade_events)}",
            f"Filled Orders:       {sum(1 for s in order_states.values() if s == 'filled')}",
            f"Rejected Orders:     {sum(1 for s in order_states.values() if s == 'rejected')}",
            f"Canceled Orders:     {sum(1 for s in order_states.values() if s == 'canceled')}",
            f"Risk Blocks:         {len(failed_risks)}",
            "==========================",
        ]
        return "\n".join(lines)
