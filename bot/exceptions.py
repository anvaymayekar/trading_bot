from __future__ import annotations

from typing import Any


class TradingBotError(Exception):
    """Base exception for all custom errors raised by the trading bot."""

    pass


class ConfigError(TradingBotError):
    """Raised when required configuration (e.g. API keys) is missing or invalid."""

    pass


class ValidationError(TradingBotError):
    """Raised for business-rule validation failures not covered by Pydantic field validation."""

    pass


class NetworkError(TradingBotError):
    """Raised when a request never received a valid response (timeout, DNS, connection reset)."""

    pass


class APIError(TradingBotError):
    """Raised when Binance responds, but with an error."""

    def __init__(
        self,
        message: str,
        binance_code: int | None = None,
        raw_response: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.binance_code = binance_code
        self.raw_response = raw_response

    def __str__(self) -> str:
        if self.binance_code is not None:
            return f"[{self.binance_code}] {super().__str__()}"
        return super().__str__()


class AuthenticationError(APIError):
    """Raised on invalid API key / signature errors (e.g. Binance code -2015)."""

    pass


class InsufficientBalanceError(APIError):
    """Raised when the account has insufficient margin/balance (e.g. Binance code -2019)."""

    pass


class InvalidSymbolError(APIError):
    """Raised when the requested symbol is not recognized by Binance (e.g. code -1121)."""

    pass


class OrderRejectedError(APIError):
    """Raised for any other order rejection returned by Binance's API."""

    pass
