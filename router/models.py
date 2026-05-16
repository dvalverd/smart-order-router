
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import time
import uuid


class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


class RoutingStrategy(str, Enum):
    BEST_PRICE = "best_price"   
    SPLIT = "split"             
    VWAP = "vwap"               
    TWAP = "twap"               


@dataclass
class Order:
    ticker: str
    side: Side
    qty: int
    order_type: OrderType = OrderType.MARKET
    limit_price: Optional[float] = None
    strategy: RoutingStrategy = RoutingStrategy.BEST_PRICE
    max_venues: int = 3
    order_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp_us: float = field(default_factory=lambda: time.time() * 1e6)

    @property
    def is_buy(self) -> bool:
        return self.side == Side.BUY


@dataclass
class Fill:
    order_id: str
    venue: str
    fill_price: float
    fill_qty: int
    gross_cost: float
    fees: float
    net_cost: float
    slippage_bps: float
    latency_us: float
    timestamp_us: float = field(default_factory=lambda: time.time() * 1e6)


@dataclass
class RoutingResult:
    order: Order
    fills: list[Fill]
    strategy: str
    arrival_price: float
    avg_fill_price: float
    total_cost: float
    total_slippage_bps: float
    vwap_deviation_bps: float
    total_latency_us: float
    venues_used: list[str] = field(default_factory=list)
    timestamp_us: float = field(default_factory=lambda: time.time() * 1e6)

    @property
    def fill_rate(self) -> float:
        filled = sum(f.fill_qty for f in self.fills)
        return filled / self.order.qty if self.order.qty > 0 else 0.0

    @property
    def total_filled(self) -> int:
        return sum(f.fill_qty for f in self.fills)

    def to_dict(self) -> dict:
        return {
            "order_id": self.order.order_id,
            "ticker": self.order.ticker,
            "side": self.order.side.value,
            "qty": self.order.qty,
            "strategy": self.strategy,
            "arrival_price": self.arrival_price,
            "avg_fill_price": self.avg_fill_price,
            "total_cost": self.total_cost,
            "slippage_bps": round(self.total_slippage_bps, 4),
            "vwap_deviation_bps": round(self.vwap_deviation_bps, 4),
            "total_latency_us": round(self.total_latency_us, 2),
            "fill_rate": round(self.fill_rate, 4),
            "venues_used": self.venues_used,
            "n_fills": len(self.fills),
        }
