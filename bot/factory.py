from __future__ import annotations

from bot.client import BinanceFuturesClient
from bot.exceptions import ValidationError
from bot.models import OrderRequest, OrderType
from bot.orders import LimitOrder, MarketOrder, OrderStrategy, TwapOrder

_STRATEGY_MAP: dict[OrderType, type[OrderStrategy]] = {
    OrderType.MARKET: MarketOrder,
    OrderType.LIMIT: LimitOrder,
    OrderType.TWAP: TwapOrder,
}


def build_strategy(
    request: OrderRequest, client: BinanceFuturesClient
) -> OrderStrategy:
    strategy_cls = _STRATEGY_MAP.get(request.order_type)
    if strategy_cls is None:
        raise ValidationError(f"Unsupported order type: {request.order_type}")
    return strategy_cls(request, client)
