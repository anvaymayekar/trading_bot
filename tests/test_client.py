from unittest.mock import MagicMock, patch

import pytest

from bot.client import BinanceFuturesClient
from bot.config import Settings
from bot.exceptions import InsufficientBalanceError, NetworkError


@pytest.fixture
def settings():
    return Settings(BINANCE_API_KEY="k", BINANCE_API_SECRET="s")


def test_sign_adds_timestamp_and_signature(settings):
    client = BinanceFuturesClient(settings)
    signed = client._sign({"symbol": "BTCUSDT"})
    assert "timestamp" in signed
    assert "signature" in signed


def test_place_order_success(settings):
    client = BinanceFuturesClient(settings)
    mock_response = MagicMock(status_code=200)
    mock_response.json.return_value = {"orderId": 1, "status": "NEW"}
    with patch.object(client._client, "post", return_value=mock_response):
        result = client.place_order("BTCUSDT", "BUY", "MARKET", "0.001")
    assert result["orderId"] == 1


def test_place_order_insufficient_balance_raises(settings):
    client = BinanceFuturesClient(settings)
    mock_response = MagicMock(status_code=400)
    mock_response.json.return_value = {"code": -2019, "msg": "Margin is insufficient"}
    with patch.object(client._client, "post", return_value=mock_response):
        with pytest.raises(InsufficientBalanceError):
            client.place_order("BTCUSDT", "BUY", "MARKET", "0.001")
