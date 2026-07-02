import pytest
from pydantic import ValidationError as PydanticValidationError

from bot.models import OrderRequest, OrderType, Side


def test_market_order_valid():
    req = OrderRequest(
        symbol="btcusdt", side=Side.BUY, order_type=OrderType.MARKET, quantity="0.001"
    )
    assert req.symbol == "BTCUSDT"


def test_limit_order_requires_price():
    with pytest.raises(PydanticValidationError):
        OrderRequest(
            symbol="BTCUSDT",
            side=Side.BUY,
            order_type=OrderType.LIMIT,
            quantity="0.001",
        )


def test_market_order_rejects_price():
    with pytest.raises(PydanticValidationError):
        OrderRequest(
            symbol="BTCUSDT",
            side=Side.BUY,
            order_type=OrderType.MARKET,
            quantity="0.001",
            price="50000",
        )


def test_quantity_must_be_positive():
    with pytest.raises(PydanticValidationError):
        OrderRequest(
            symbol="BTCUSDT", side=Side.BUY, order_type=OrderType.MARKET, quantity="-1"
        )


def test_twap_requires_slices_and_interval():
    with pytest.raises(PydanticValidationError):
        OrderRequest(
            symbol="BTCUSDT", side=Side.BUY, order_type=OrderType.TWAP, quantity="0.01"
        )
