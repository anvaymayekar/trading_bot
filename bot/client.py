from __future__ import annotations

import hashlib
import hmac
import logging
import time
from functools import wraps
from typing import Any, Callable
from urllib.parse import urlencode

import httpx

from bot.config import Settings, get_settings
from bot.exceptions import (
    APIError,
    AuthenticationError,
    InsufficientBalanceError,
    InvalidSymbolError,
    NetworkError,
    OrderRejectedError,
)

logger = logging.getLogger("trading_bot")

BINANCE_ERROR_MAP: dict[int, type[APIError]] = {
    -2015: AuthenticationError,
    -2019: InsufficientBalanceError,
    -1121: InvalidSymbolError,
}


def with_retry(max_attempts: int = 3, backoff_seconds: float = 1.0) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except NetworkError as exc:
                    last_exc = exc
                    logger.debug(
                        "Retry %s/%s after network error: %s",
                        attempt,
                        max_attempts,
                        exc,
                    )
                    if attempt < max_attempts:
                        time.sleep(backoff_seconds * attempt)
            raise last_exc  # type: ignore[misc]

        return wrapper

    return decorator


class BinanceFuturesClient:
    """Thin, typed wrapper around Binance Futures Testnet REST endpoints."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = httpx.Client(
            base_url=self._settings.binance_base_url,
            headers={"X-MBX-APIKEY": self._settings.binance_api_key},
            timeout=10.0,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "BinanceFuturesClient":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()

    def _sign(self, params: dict[str, Any]) -> dict[str, Any]:
        params = dict(params)
        params["timestamp"] = int(time.time() * 1000)
        query_string = urlencode(params)
        signature = hmac.new(
            self._settings.binance_api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    @with_retry(max_attempts=3)
    def _signed_post(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        signed_params = self._sign(params)
        logger.debug(
            "Request: POST %s params=%s",
            path,
            {k: v for k, v in signed_params.items() if k != "signature"},
        )
        try:
            response = self._client.post(path, params=signed_params)
        except httpx.TimeoutException as exc:
            logger.error("Request to %s timed out: %s", path, exc)
            raise NetworkError(f"Request to {path} timed out") from exc
        except httpx.ConnectError as exc:
            logger.error("Could not connect to Binance testnet: %s", exc)
            raise NetworkError(f"Could not connect to Binance testnet: {exc}") from exc
        except httpx.HTTPError as exc:
            logger.error("Network error calling %s: %s", path, exc)
            raise NetworkError(f"Network error calling {path}: {exc}") from exc

        return self._handle_response(response)

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        try:
            body = response.json()
        except ValueError:
            body = {}

        logger.debug("Response: status=%s body=%s", response.status_code, body)

        if response.status_code >= 400:
            code = body.get("code")
            msg = body.get("msg", f"HTTP {response.status_code} error")
            logger.error("API error: code=%s msg=%s", code, msg)
            exc_cls = BINANCE_ERROR_MAP.get(code, OrderRejectedError)
            raise exc_cls(msg, binance_code=code, raw_response=body)

        return body

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: str,
        price: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
        }
        if order_type == "LIMIT":
            params["price"] = price
            params["timeInForce"] = "GTC"

        return self._signed_post("/fapi/v1/order", params)
