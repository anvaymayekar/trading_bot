from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from bot.exceptions import ConfigError


class Settings(BaseSettings):
    """Typed application configuration, loaded from environment variables / .env."""

    binance_api_key: str = Field(..., alias="BINANCE_API_KEY")
    binance_api_secret: str = Field(..., alias="BINANCE_API_SECRET")
    binance_base_url: str = Field(
        default="https://testnet.binancefuture.com",
        alias="BINANCE_BASE_URL",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()
    except Exception as exc:
        raise ConfigError(
            "Missing or invalid configuration. "
            "Check that .env exists and contains BINANCE_API_KEY and BINANCE_API_SECRET."
        ) from exc
