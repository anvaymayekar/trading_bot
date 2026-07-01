from __future__ import annotations

import time
from abc import ABC, abstractmethod
from decimal import Decimal

from bot.client import BinanceFuturesClient
from bot.exceptions import ValidationError
from bot.models import (
    OrderRequest,
    OrderResponse,
    OrderType,
    TwapExecutionSummary,
)


class OrderStrategy(ABC):
    """Encapsulates how a given order type validates itself and executes
    against the exchange client."""

    def __init__(self, request: OrderRequest, client: BinanceFuturesClient) -> None:
        self.request = request
        self.client = client

    @abstractmethod
    def execute(self) -> OrderResponse | TwapExecutionSummary: ...


class MarketOrder(OrderStrategy):
    def execute(self) -> OrderResponse:
        raw = self.client.place_order(
            symbol=self.request.symbol,
            side=self.request.side.value,
            order_type=OrderType.MARKET.value,
            quantity=str(self.request.quantity),
        )
        return OrderResponse.from_binance_response(raw, OrderType.MARKET)


class LimitOrder(OrderStrategy):
    def execute(self) -> OrderResponse:
        if self.request.price is None:
            raise ValidationError("price is required for LIMIT orders")

        raw = self.client.place_order(
            symbol=self.request.symbol,
            side=self.request.side.value,
            order_type=OrderType.LIMIT.value,
            quantity=str(self.request.quantity),
            price=str(self.request.price),
        )
        return OrderResponse.from_binance_response(raw, OrderType.LIMIT)


class TwapOrder(OrderStrategy):
    def execute(self) -> TwapExecutionSummary:
        slices = self.request.twap_slices
        interval = self.request.twap_interval_seconds
        if slices is None or interval is None:
            raise ValidationError(
                "twap_slices and twap_interval_seconds are required for TWAP orders"
            )

        slice_qty = self.request.quantity / slices
        results: list[OrderResponse] = []

        for i in range(slices):
            raw = self.client.place_order(
                symbol=self.request.symbol,
                side=self.request.side.value,
                order_type=OrderType.MARKET.value,
                quantity=str(slice_qty),
            )
            results.append(OrderResponse.from_binance_response(raw, OrderType.MARKET))
            if i < slices - 1:
                time.sleep(interval)

        return self._summarize(results)

    def _summarize(self, results: list[OrderResponse]) -> TwapExecutionSummary:
        total_executed = sum((r.executed_qty for r in results), Decimal("0"))
        priced = [r for r in results if r.avg_price is not None]
        avg_price = (
            sum((r.avg_price * r.executed_qty for r in priced), Decimal("0"))
            / total_executed
            if priced and total_executed > 0
            else None
        )
        return TwapExecutionSummary(
            symbol=self.request.symbol,
            side=self.request.side,
            total_quantity=self.request.quantity,
            total_executed_qty=total_executed,
            avg_price=avg_price,
            slice_orders=results,
        )
