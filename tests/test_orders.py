from unittest.mock import MagicMock

from bot.models import OrderRequest, OrderType, Side
from bot.orders import LimitOrder, MarketOrder, TwapOrder


def _binance_response(order_id=1, executed_qty="0.001", avg_price="50000"):
    return {
        "orderId": order_id,
        "symbol": "BTCUSDT",
        "side": "BUY",
        "status": "FILLED",
        "executedQty": executed_qty,
        "avgPrice": avg_price,
    }


def test_market_order_execute():
    client = MagicMock()
    client.place_order.return_value = _binance_response()
    request = OrderRequest(
        symbol="BTCUSDT", side=Side.BUY, order_type=OrderType.MARKET, quantity="0.001"
    )
    result = MarketOrder(request, client).execute()
    assert result.order_id == 1
    assert result.avg_price == 50000


def test_limit_order_execute():
    client = MagicMock()
    client.place_order.return_value = _binance_response()
    request = OrderRequest(
        symbol="BTCUSDT",
        side=Side.BUY,
        order_type=OrderType.LIMIT,
        quantity="0.001",
        price="50000",
    )
    result = LimitOrder(request, client).execute()
    assert client.place_order.call_args.kwargs["price"] == "50000"
    assert result.status.value == "FILLED"


def test_twap_order_execute_places_correct_slice_count():
    client = MagicMock()
    client.place_order.return_value = _binance_response(
        executed_qty="0.001", avg_price="50000"
    )
    request = OrderRequest(
        symbol="BTCUSDT",
        side=Side.BUY,
        order_type=OrderType.TWAP,
        quantity="0.003",
        twap_slices=3,
        twap_interval_seconds=0,
    )
    result = TwapOrder(request, client).execute()
    assert client.place_order.call_count == 3
    assert result.total_executed_qty == 0.003
