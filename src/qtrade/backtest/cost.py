from qtrade.core.types import OrderDirection


class CostModel:
    """A股交易成本模型"""

    def __init__(
        self,
        commission_rate: float = 0.0003,
        min_commission: float = 5.0,
        stamp_tax_rate: float = 0.0005,
        transfer_fee_rate: float = 0.00001,
    ):
        self.commission_rate = commission_rate
        self.min_commission = min_commission
        self.stamp_tax_rate = stamp_tax_rate
        self.transfer_fee_rate = transfer_fee_rate

    def calculate(self, volume: float, price: float, direction: OrderDirection) -> dict:
        value = volume * price

        commission = max(value * self.commission_rate, self.min_commission)
        tax = value * self.stamp_tax_rate if direction == OrderDirection.SHORT else 0.0
        transfer_fee = value * self.transfer_fee_rate

        total_cost = commission + tax + transfer_fee

        return {
            "commission": commission,
            "tax": tax,
            "transfer_fee": transfer_fee,
            "total": total_cost,
        }


class SlippageModel:
    def __init__(self, slippage_rate: float = 0.001):
        self.slippage_rate = slippage_rate

    def calculate_price(
        self, original_price: float, direction: OrderDirection
    ) -> float:
        if direction == OrderDirection.LONG:
            return original_price * (1 + self.slippage_rate)
        else:
            return original_price * (1 - self.slippage_rate)
