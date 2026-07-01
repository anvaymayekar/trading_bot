"""Throwaway manual test script — not part of the final submission.
Confirms BinanceFuturesClient can place a real order against testnet."""

from bot.client import BinanceFuturesClient


def main():
    with BinanceFuturesClient() as client:
        response = client.place_order(
            symbol="BTCUSDT",
            side="BUY",
            order_type="MARKET",
            quantity="0.001",
        )
        print("Raw response:")
        print(response)


if __name__ == "__main__":
    main()
