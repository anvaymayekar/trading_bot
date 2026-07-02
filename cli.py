from __future__ import annotations

from decimal import Decimal, InvalidOperation

import typer
from rich.console import Console
from rich.table import Table

from bot.client import BinanceFuturesClient
from bot.exceptions import TradingBotError
from bot.factory import build_strategy
from bot.logging_config import setup_logging
from bot.models import OrderRequest, OrderType, Side, TwapExecutionSummary

app = typer.Typer(help="Place orders on Binance Futures Testnet.")
console = Console()
logger = setup_logging()


@app.command()
def place_order(
    symbol: str = typer.Option(..., help="Trading symbol, e.g. BTCUSDT"),
    side: Side = typer.Option(..., help="BUY or SELL"),
    order_type: OrderType = typer.Option(..., "--order-type", help="MARKET or LIMIT"),
    quantity: str = typer.Option(..., help="Order quantity"),
    price: str | None = typer.Option(None, help="Required for LIMIT orders"),
) -> None:
    """Place a MARKET or LIMIT order."""
    _run_order(symbol, side, order_type, quantity, price)


@app.command()
def twap(
    symbol: str = typer.Option(..., help="Trading symbol, e.g. BTCUSDT"),
    side: Side = typer.Option(..., help="BUY or SELL"),
    quantity: str = typer.Option(..., help="Total quantity across all slices"),
    slices: int = typer.Option(..., help="Number of slices"),
    interval: int = typer.Option(..., help="Seconds to wait between slices"),
) -> None:
    """Place a TWAP order: quantity split into timed MARKET slices."""
    _run_order(
        symbol,
        side,
        OrderType.TWAP,
        quantity,
        price=None,
        twap_slices=slices,
        twap_interval_seconds=interval,
    )


def _run_order(
    symbol: str,
    side: Side,
    order_type: OrderType,
    quantity: str,
    price: str | None,
    twap_slices: int | None = None,
    twap_interval_seconds: int | None = None,
) -> None:
    try:
        request = OrderRequest(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=_to_decimal(quantity, "quantity"),
            price=_to_decimal(price, "price") if price is not None else None,
            twap_slices=twap_slices,
            twap_interval_seconds=twap_interval_seconds,
        )
    except Exception as exc:
        console.print(f"[red]Invalid input:[/red] {exc}")
        logger.error("Validation failed: %s", exc)
        raise typer.Exit(code=1)

    _print_request_summary(request)
    logger.info(
        "Placing %s %s order: symbol=%s quantity=%s",
        request.order_type.value,
        request.side.value,
        request.symbol,
        request.quantity,
    )

    try:
        with BinanceFuturesClient() as client:
            strategy = build_strategy(request, client)
            result = strategy.execute()
    except TradingBotError as exc:
        console.print(f"[red]Order failed:[/red] {exc}")
        logger.error("Order failed: %s", exc)
        raise typer.Exit(code=1)

    if isinstance(result, TwapExecutionSummary):
        logger.info(
            "TWAP accepted: total_executed_qty=%s avg_price=%s slices=%s",
            result.total_executed_qty,
            result.avg_price,
            len(result.slice_orders),
        )
    else:
        logger.info(
            "Order accepted: id=%s executed_qty=%s avg_price=%s",
            result.order_id,
            result.executed_qty,
            result.avg_price,
        )
    _print_result(result)
    console.print("[green]Success[/green]")


def _to_decimal(value: str, field_name: str) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation:
        raise ValueError(f"{field_name} must be a valid number, got: {value}")


def _print_request_summary(request: OrderRequest) -> None:
    table = Table(title="Order Request")
    table.add_column("Field")
    table.add_column("Value")
    for field, value in request.model_dump(exclude_none=True, mode="json").items():
        table.add_row(field, str(value))
    console.print(table)


def _print_result(result: object) -> None:
    if isinstance(result, TwapExecutionSummary):
        console.print(
            f"TWAP complete: {result.total_executed_qty}/{result.total_quantity} filled, "
            f"avg_price={result.avg_price}"
        )
        for i, order in enumerate(result.slice_orders, start=1):
            console.print(
                f"  slice {i}: orderId={order.order_id} status={order.status.value}"
            )
    else:
        console.print(
            f"orderId={result.order_id} status={result.status.value} "
            f"executedQty={result.executed_qty} avgPrice={result.avg_price}"
        )


if __name__ == "__main__":
    app()
