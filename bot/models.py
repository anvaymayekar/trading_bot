from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    TWAP = "TWAP"


class OrderStatus(str, Enum):
    NEW = "NEW"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    REJECTED = "REJECTED"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"


class OrderRequest(BaseModel):
    """Validated representation of a user's order intent, before it becomes
    an exchange-specific payload."""

    symbol: str = Field(..., min_length=1)
    side: Side
    order_type: OrderType
    quantity: Decimal = Field(..., gt=0)
    price: Decimal | None = Field(default=None, gt=0)

    # TWAP-specific, only relevant when order_type == TWAP
    twap_slices: int | None = Field(default=None, gt=0)
    twap_interval_seconds: int | None = Field(default=None, gt=0)

    @field_validator("symbol")
    @classmethod
    def symbol_uppercase(cls, v: str) -> str:
        return v.strip().upper()

    @model_validator(mode="after")
    def check_type_specific_fields(self) -> "OrderRequest":
        if self.order_type == OrderType.LIMIT and self.price is None:
            raise ValueError("price is required for LIMIT orders")

        if self.order_type == OrderType.TWAP:
            if self.twap_slices is None or self.twap_interval_seconds is None:
                raise ValueError(
                    "twap_slices and twap_interval_seconds are required for TWAP orders"
                )

        if self.order_type == OrderType.MARKET and self.price is not None:
            raise ValueError("price must not be set for MARKET orders")

        return self


class OrderResponse(BaseModel):
    order_id: int
    symbol: str
    side: Side
    order_type: OrderType
    status: OrderStatus
    executed_qty: Decimal
    avg_price: Decimal | None = None
    raw_response: dict[str, Any] = Field(default_factory=dict, repr=False)

    @classmethod
    def from_binance_response(
        cls, data: dict[str, Any], order_type: OrderType
    ) -> "OrderResponse":
        avg_price_raw = data.get("avgPrice")
        avg_price = (
            Decimal(avg_price_raw)
            if avg_price_raw not in (None, "", "0.00", "0")
            else None
        )
        return cls(
            order_id=data["orderId"],
            symbol=data["symbol"],
            side=Side(data["side"]),
            order_type=order_type,
            status=OrderStatus(data["status"]),
            executed_qty=Decimal(data.get("executedQty", "0")),
            avg_price=avg_price,
            raw_response=data,
        )


class TwapExecutionSummary(BaseModel):
    """Aggregated result of a TWAP execution across all its slices."""

    symbol: str
    side: Side
    total_quantity: Decimal
    total_executed_qty: Decimal
    avg_price: Decimal | None
    slice_orders: list[OrderResponse]
