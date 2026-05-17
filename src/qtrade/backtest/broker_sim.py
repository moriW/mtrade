from typing import Dict, List, Optional
from datetime import date
from enum import Enum

from qtrade.backtest.events import OrderEvent, TradeEvent, AccountEvent, EventBus
from qtrade.backtest.cost import CostModel, SlippageModel
from qtrade.core.types import OrderDirection
from qtrade.core.log import get_logger

logger = get_logger("broker_sim")


class ExecutionMode(str, Enum):
    OPEN = "open"
    CLOSE = "close"
    VWAP = "vwap"


class OrderState:
    VALID_TRANSITIONS = {
        "new": {"submitted", "rejected", "canceled"},
        "submitted": {"partial", "filled", "canceled", "rejected"},
        "partial": {"filled", "canceled", "partial"},
        "filled": set(),
        "canceled": set(),
        "rejected": set(),
    }

    @staticmethod
    def transition(current: str, target: str) -> bool:
        if target not in OrderState.VALID_TRANSITIONS.get(current, set()):
            logger.warning("Invalid state transition", current=current, target=target)
            return False
        return True


class SimulatedBroker:
    def __init__(
        self,
        event_bus: EventBus,
        bars: dict,
        initial_cash: float = 1000000.0,
        execution_mode: ExecutionMode = ExecutionMode.OPEN,
        cost_model: Optional[CostModel] = None,
        slippage_model: Optional[SlippageModel] = None,
    ):
        self.event_bus = event_bus
        self.bars = bars
        self.cash = initial_cash
        self.frozen_cash: float = 0.0
        self.positions: Dict[str, float] = {}
        self.available_volume: Dict[str, float] = {}
        self.locked_volume: Dict[str, float] = {}
        self.execution_mode = execution_mode
        self.cost_model = cost_model or CostModel()
        self.slippage_model = slippage_model or SlippageModel()

        self.orders: Dict[str, OrderEvent] = {}
        self.trades: List[TradeEvent] = []

    def submit_order(self, order: OrderEvent) -> bool:
        if order.order_id in self.orders:
            logger.warning("Duplicate order", order_id=order.order_id)
            return False

        OrderState.transition("new", "submitted")
        order.status = "submitted"
        self.orders[order.order_id] = order
        self.event_bus.publish(order)
        return True

    def process_orders(self, trade_date: date):
        submitted = [o for o in self.orders.values() if o.status == "submitted"]
        for order in submitted:
            bar = self.bars.get((trade_date, order.symbol))
            if bar is None:
                continue

            if bar.get("is_suspended", False):
                self._reject_order(order, "symbol suspended")
                continue

            exec_price = self._get_execution_price(bar, order.direction)
            if exec_price is None:
                self._reject_order(order, "no valid execution price")
                continue

            if order.direction == "long":
                self._execute_buy(order, trade_date, exec_price, bar)
            elif order.direction == "short":
                self._execute_sell(order, trade_date, exec_price, bar)

    def _get_execution_price(self, bar: dict, direction: str) -> Optional[float]:
        if self.execution_mode == ExecutionMode.OPEN:
            p = bar["open"]
        elif self.execution_mode == ExecutionMode.CLOSE:
            p = bar["close"]
        elif self.execution_mode == ExecutionMode.VWAP:
            p = (bar["high"] + bar["low"] + bar["close"]) / 3
        else:
            return None

        if direction == "long":
            limit_up = bar.get("limit_up") or float("inf")
            if p >= limit_up - 1e-5:
                return None
        else:
            limit_down = bar.get("limit_down") or 0.0
            if p <= limit_down + 1e-5:
                return None

        return p

    def _execute_buy(
        self, order: OrderEvent, trade_date: date, price: float, bar: dict
    ):
        exec_p = self.slippage_model.calculate_price(price, OrderDirection.LONG)
        cost = self.cost_model.calculate(order.volume, exec_p, OrderDirection.LONG)
        required = order.volume * exec_p + cost["total"]

        if self.cash < required:
            max_vol = (
                int((self.cash - cost.get("commission", 5)) / (exec_p * 100)) * 100
            )
            if max_vol < 100:
                self._reject_order(order, "insufficient cash")
                return
            order.volume = max_vol
            cost = self.cost_model.calculate(order.volume, exec_p, OrderDirection.LONG)
            required = order.volume * exec_p + cost["total"]

        self.cash -= required
        self.positions[order.symbol] = (
            self.positions.get(order.symbol, 0) + order.volume
        )
        self.locked_volume[order.symbol] = (
            self.locked_volume.get(order.symbol, 0) + order.volume
        )

        order.filled_volume = order.volume
        order.filled_price = exec_p
        OrderState.transition("submitted", "filled")
        order.status = "filled"

        trade = TradeEvent(
            order_id=order.order_id,
            trade_date=trade_date,
            symbol=order.symbol,
            direction=order.direction,
            price=exec_p,
            volume=order.volume,
            commission=cost["commission"],
            tax=cost["tax"],
            transfer_fee=cost["transfer_fee"],
        )
        self.trades.append(trade)
        self.event_bus.publish(trade)
        self.event_bus.publish(order)

    def _execute_sell(
        self, order: OrderEvent, trade_date: date, price: float, bar: dict
    ):
        max_sell = self.available_volume.get(order.symbol, 0)
        if max_sell <= 0:
            self._reject_order(order, "no available shares (T+1 locked)")
            return

        exec_vol = min(order.volume, max_sell)
        exec_p = self.slippage_model.calculate_price(price, OrderDirection.SHORT)
        cost = self.cost_model.calculate(exec_vol, exec_p, OrderDirection.SHORT)

        self.cash += exec_vol * exec_p - cost["total"]
        self.positions[order.symbol] -= exec_vol
        self.available_volume[order.symbol] -= exec_vol
        if self.positions[order.symbol] <= 1e-5:
            self.positions[order.symbol] = 0.0

        order.filled_volume = exec_vol
        order.filled_price = exec_p
        order.status = "filled" if exec_vol == order.volume else "partial"
        OrderState.transition("submitted", order.status)
        order.status = order.status

        trade = TradeEvent(
            order_id=order.order_id,
            trade_date=trade_date,
            symbol=order.symbol,
            direction=order.direction,
            price=exec_p,
            volume=exec_vol,
            commission=cost["commission"],
            tax=cost["tax"],
            transfer_fee=cost["transfer_fee"],
        )
        self.trades.append(trade)
        self.event_bus.publish(trade)
        self.event_bus.publish(order)

    def _reject_order(self, order: OrderEvent, reason: str):
        OrderState.transition(order.status, "rejected")
        order.status = "rejected"
        order.reject_reason = reason
        self.event_bus.publish(order)
        logger.info("Order rejected", order_id=order.order_id, reason=reason)

    def end_of_day_settlement(self, trade_date: date):
        for sym in self.locked_volume:
            self.available_volume[sym] = (
                self.available_volume.get(sym, 0) + self.locked_volume[sym]
            )
        self.locked_volume.clear()

        self.event_bus.publish(
            AccountEvent(
                trade_date=trade_date,
                cash=self.cash,
                frozen_cash=self.frozen_cash,
                positions=self.positions.copy(),
            )
        )

    def get_account_state(self, prices: Dict[str, float]) -> dict:
        total_value = self.cash
        for sym, vol in self.positions.items():
            total_value += vol * prices.get(sym, 0.0)
        return {
            "cash": self.cash,
            "frozen_cash": self.frozen_cash,
            "positions": self.positions.copy(),
            "total_value": total_value,
            "prices": prices,
        }
