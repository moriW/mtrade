from datetime import date, datetime
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, RootModel


class Symbol(RootModel[str]):
    """股票代码，如 000001.SZ"""

    pass


class OrderDirection(str, Enum):
    """订单方向"""

    LONG = "long"
    SHORT = "short"  # 卖出


class OrderType(str, Enum):
    """订单类型"""

    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(str, Enum):
    """订单状态"""

    NEW = "new"
    SUBMITTED = "submitted"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"


class Bar(BaseModel):
    """日线行情 (K线)"""

    trade_date: date
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float  # 成交量
    amount: float  # 成交额
    adj_factor: float = 1.0  # 复权因子
    limit_up: Optional[float] = None  # 涨停价
    limit_down: Optional[float] = None  # 跌停价
    is_suspended: bool = False  # 是否停牌


class Signal(BaseModel):
    """策略信号"""

    trade_date: date
    symbol: str
    score: float
    direction: OrderDirection
    horizon: int = 1
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TargetPosition(BaseModel):
    """目标持仓"""

    trade_date: date
    symbol: str
    weight: Optional[float] = None  # 目标权重
    target_volume: Optional[float] = None  # 目标股数 (如有精确要求)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Order(BaseModel):
    """交易订单"""

    order_id: str
    symbol: str
    trade_date: date
    direction: OrderDirection
    order_type: OrderType
    price: float
    volume: float
    status: OrderStatus = OrderStatus.NEW
    filled_volume: float = 0.0
    filled_price: float = 0.0
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Trade(BaseModel):
    """成交记录"""

    trade_id: str
    order_id: str
    symbol: str
    trade_date: date
    trade_time: datetime
    direction: OrderDirection
    price: float
    volume: float
    commission: float = 0.0  # 佣金
    tax: float = 0.0  # 印花税
    transfer_fee: float = 0.0  # 过户费


class Position(BaseModel):
    """单票持仓"""

    symbol: str
    volume: float
    available_volume: float  # T+1 可用数量
    avg_price: float


class Account(BaseModel):
    """资金账户"""

    account_id: str
    cash: float
    frozen_cash: float = 0.0
    positions: Dict[str, Position] = Field(default_factory=dict)

    @property
    def total_asset(self) -> float:
        """总资产（需要外部提供当前最新价格，暂时只计算现金部分，实际总资产需根据Position动态计算）"""
        # 注意：严格意义上总资产需要依据最新市价计算。这里仅做占位。
        return self.cash + self.frozen_cash
