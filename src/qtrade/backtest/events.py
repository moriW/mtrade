from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import date, datetime
from pydantic import BaseModel, Field
import uuid


class EventType(str, Enum):
    MARKET_DATA = "market_data"
    SIGNAL = "signal"
    ORDER = "order"
    TRADE = "trade"
    RISK = "risk"
    ACCOUNT = "account"


class BaseEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MarketDataEvent(BaseEvent):
    event_type: EventType = EventType.MARKET_DATA
    trade_date: date
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float
    limit_up: Optional[float] = None
    limit_down: Optional[float] = None
    is_suspended: bool = False


class SignalEvent(BaseEvent):
    event_type: EventType = EventType.SIGNAL
    trade_date: date
    symbol: str
    score: float
    direction: str = "long"
    horizon: int = 1


class OrderEvent(BaseEvent):
    event_type: EventType = EventType.ORDER
    order_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trade_date: date
    symbol: str
    direction: str
    price: float
    volume: float
    status: str = "new"
    filled_volume: float = 0.0
    filled_price: float = 0.0
    canceled: bool = False
    reject_reason: Optional[str] = None


class TradeEvent(BaseEvent):
    event_type: EventType = EventType.TRADE
    trade_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str
    trade_date: date
    symbol: str
    direction: str
    price: float
    volume: float
    commission: float = 0.0
    tax: float = 0.0
    transfer_fee: float = 0.0


class RiskEvent(BaseEvent):
    event_type: EventType = EventType.RISK
    order_id: Optional[str] = None
    rule_name: str
    passed: bool
    reason: Optional[str] = None


class AccountEvent(BaseEvent):
    event_type: EventType = EventType.ACCOUNT
    trade_date: date
    cash: float
    frozen_cash: float = 0.0
    positions: Dict[str, float] = Field(default_factory=dict)


class EventBus:
    def __init__(self):
        self._queue: List[BaseEvent] = []
        self._history: List[BaseEvent] = []

    def publish(self, event: BaseEvent):
        self._queue.append(event)
        self._history.append(event)

    def next(self) -> Optional[BaseEvent]:
        if self._queue:
            return self._queue.pop(0)
        return None

    def pending_count(self) -> int:
        return len(self._queue)

    def get_history(self, event_type: Optional[EventType] = None) -> List[BaseEvent]:
        if event_type is None:
            return self._history
        return [e for e in self._history if e.event_type == event_type]
