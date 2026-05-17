from typing import Optional, List
from dataclasses import dataclass
from qtrade.backtest.events import OrderEvent, RiskEvent
from qtrade.core.log import get_logger

logger = get_logger("risk_engine")


@dataclass
class RiskRule:
    name: str = ""

    def check(self, order: OrderEvent, account: dict, positions: dict) -> RiskEvent:
        raise NotImplementedError


class SingleStockWeightRule(RiskRule):
    def __init__(self, max_weight: float = 0.05):
        super().__init__(name="single_stock_weight")
        self.max_weight = max_weight

    def check(self, order: OrderEvent, account: dict, positions: dict) -> RiskEvent:
        total_asset = account["total_value"]
        prices_lookup = account.get("prices", {})

        existing_val = positions.get(order.symbol, 0) * prices_lookup.get(
            order.symbol, 0
        )
        new_val = order.volume * order.price if order.direction == "long" else 0
        weight = (existing_val + new_val) / total_asset if total_asset > 0 else 1.0

        if weight > self.max_weight:
            return RiskEvent(
                order_id=order.order_id,
                rule_name=self.name,
                passed=False,
                reason=f"weight {weight:.4f} exceeds {self.max_weight}",
            )
        return RiskEvent(order_id=order.order_id, rule_name=self.name, passed=True)


class SingleOrderAmountRule(RiskRule):
    def __init__(self, max_amount: float = 500000.0):
        super().__init__(name="single_order_amount")
        self.max_amount = max_amount

    def check(self, order: OrderEvent, account: dict, positions: dict) -> RiskEvent:
        amount = order.volume * order.price
        if amount > self.max_amount:
            return RiskEvent(
                order_id=order.order_id,
                rule_name=self.name,
                passed=False,
                reason=f"amount {amount:.0f} exceeds {self.max_amount}",
            )
        return RiskEvent(order_id=order.order_id, rule_name=self.name, passed=True)


class CashConstraintRule(RiskRule):
    def check(self, order: OrderEvent, account: dict, positions: dict) -> RiskEvent:
        if order.direction != "long":
            return RiskEvent(order_id=order.order_id, rule_name=self.name, passed=True)

        required = order.volume * order.price
        if required > account["cash"]:
            return RiskEvent(
                order_id=order.order_id,
                rule_name=self.name,
                passed=False,
                reason=f"cash {account['cash']:.0f} < required {required:.0f}",
            )
        return RiskEvent(order_id=order.order_id, rule_name=self.name, passed=True)


class TotalPositionRule(RiskRule):
    def __init__(self, max_position: float = 0.95):
        super().__init__(name="total_position")
        self.max_position = max_position

    def check(self, order: OrderEvent, account: dict, positions: dict) -> RiskEvent:
        total_asset = account["total_value"]
        prices_lookup = account.get("prices", {})

        pos_value = sum(
            vol * prices_lookup.get(sym, 0) for sym, vol in positions.items()
        )
        ratio = pos_value / total_asset if total_asset > 0 else 0

        if order.direction == "long" and ratio > self.max_position:
            return RiskEvent(
                order_id=order.order_id,
                rule_name=self.name,
                passed=False,
                reason=f"position ratio {ratio:.4f} exceeds {self.max_position}",
            )
        return RiskEvent(order_id=order.order_id, rule_name=self.name, passed=True)


class RiskEngine:
    def __init__(self, rules: Optional[List[RiskRule]] = None):
        self.rules = rules or [
            SingleStockWeightRule(max_weight=0.05),
            SingleOrderAmountRule(max_amount=500000.0),
            CashConstraintRule(),
            TotalPositionRule(max_position=0.95),
        ]

    def check_order(
        self, order: OrderEvent, account: dict, positions: dict
    ) -> List[RiskEvent]:
        results = []
        for rule in self.rules:
            result = rule.check(order, account, positions)
            results.append(result)
            if not result.passed:
                logger.warning(
                    "Risk check failed",
                    rule=rule.name,
                    reason=result.reason,
                    order_id=order.order_id,
                )
        return results

    def is_approved(self, results: List[RiskEvent]) -> bool:
        return all(r.passed for r in results)
