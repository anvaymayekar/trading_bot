# 📈 **Trading Bot**: A Binance Futures Testnet Execution Engine

A typed, OOP-structured Python bot that places Market, Limit, and TWAP orders on Binance Futures Testnet (USDT-M) via a hand-signed REST client.

---

## 📌 Highlights

> 🧱 **Strategy Pattern** — `MarketOrder`, `LimitOrder`, `TwapOrder` all implement one `OrderStrategy` ABC. New order types don't touch the CLI or client.
>
> 🔐 **Hand-Rolled HMAC Signing** — No `python-binance` abstraction. Requests are timestamped and HMAC-SHA256 signed manually against Binance's raw REST spec.
>
> 🧬 **Typed & Validated** — `Decimal` throughout (never `float`, to avoid rounding errors on money); Pydantic enforces both field-level and cross-field rules (e.g. LIMIT requires a price).
>
> 🧯 **Structured Exceptions** — `TradingBotError` → `ValidationError` / `NetworkError` / `APIError` (→ `AuthenticationError`, `InsufficientBalanceError`, `InvalidSymbolError`). Binance error codes map to specific typed exceptions.
>
> 🪵 **Two-Tier Logging** — File captures full `DEBUG` request/response detail; console stays clean at `INFO`. No secrets logged.
>
> ⏱️ **Bonus: TWAP** — Splits quantity into N timed MARKET slices to reduce market impact — a first-class strategy, not a bolted-on script.

---

## 🧠 Approach

Three layers that don't leak into each other: `client.py` is pure transport (doesn't know what a "Limit order" is), `orders.py`/`models.py` are pure domain logic (don't know what HTTP is), `cli.py` is a thin orchestrator. Each layer is independently testable — client tests mock HTTP, order tests mock the client.

Types double as documentation. `Side`/`OrderType` are enums so a typo fails at validation, not three calls deep in a Binance error. `Decimal` everywhere money is involved, since `float` silently loses precision on values like `0.1 + 0.2`.

The exception hierarchy exists so callers can catch as narrowly (`InsufficientBalanceError`) or broadly (`TradingBotError`) as the situation needs — a flat `except Exception` tells you nothing actionable.

One decorator in the whole codebase (`@with_retry`, on network calls only) — it's used because retry is a genuine cross-cutting concern, not applied elsewhere where the idiomatic tool already exists (Typer's own decorators, Pydantic's validators).

Binance's `POST /order` response reflects order _acceptance_, not settlement — `executedQty`/`avgPrice` often show `0`/`None` even on orders that fill moments later. This is surfaced honestly rather than hidden; see Assumptions.

---

## 📁 Project Structure

```
trading_bot/
├── bot/
│   ├── client.py            # HMAC signing, HTTP transport, retry, error translation
│   ├── models.py             # Enums, OrderRequest, OrderResponse, TwapExecutionSummary
│   ├── orders.py             # OrderStrategy ABC — Market/Limit/Twap
│   ├── factory.py            # Builds the correct strategy from a validated request
│   ├── exceptions.py         # TradingBotError hierarchy
│   ├── logging_config.py     # Two-tier logging (file: DEBUG, console: INFO)
│   └── config.py             # Typed .env loading via pydantic-settings
├── cli.py                    # Typer entry point
├── tests/                     # Mocked HTTP/client — no live calls needed
├── logs_sample/               # Committed evidence: real MARKET/LIMIT/TWAP runs
├── .env.example
└── pyproject.toml
```

---

## ⚙️ Core Components

| Component                        | Responsibility                                                                |
| -------------------------------- | ----------------------------------------------------------------------------- |
| `BinanceFuturesClient`           | Signs/sends requests; translates error codes; retries transient failures only |
| `OrderStrategy` (ABC)            | Contract every order type satisfies: validate, execute, return typed result   |
| `TwapOrder`                      | Slices quantity across N timed MARKET orders, aggregates into a summary       |
| `OrderRequest` / `OrderResponse` | Typed, validated request/response models                                      |
| `Settings`                       | Typed `.env` config via `pydantic-settings`                                   |
| `TradingBotError` hierarchy      | Precise, catchable error types                                                |

---

## 🔩 Dependencies

`httpx` · `pydantic` / `pydantic-settings` · `typer` · `rich` · `pytest` / `pytest-mock` / `respx` (dev). All declared in `pyproject.toml` — no `requirements.txt`.

---

## 🚀 Setup

**1. Get testnet credentials** — [testnet.binancefuture.com](https://testnet.binancefuture.com), log in with GitHub, generate an HMAC API key pair. This is a separate sandbox from real Binance — **no KYC required.**

**2. Clone and enter**

```bash
git clone https://github.com/<your-username>/trading_bot.git
cd trading_bot
```

**3. Create a virtual environment**

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**4. Install**

```bash
pip install -e ".[dev]"
```

**5. Configure credentials**

```bash
cp .env.example .env      # macOS/Linux — use `copy` on Windows
```

Fill in your own `BINANCE_API_KEY` / `BINANCE_API_SECRET` in `.env`.

---

## ▶️ Running

```bash
# Market
python cli.py place-order --symbol BTCUSDT --side BUY --order-type MARKET --quantity 0.001

# Limit
python cli.py place-order --symbol BTCUSDT --side BUY --order-type LIMIT --quantity 0.001 --price 50000

# TWAP (bonus)
python cli.py twap --symbol BTCUSDT --side BUY --quantity 0.003 --slices 3 --interval 5
```

Each run prints a request summary, the parsed response (`orderId`, `status`, `executedQty`, `avgPrice`), and a success/failure line. Full detail is written to `logs/trades.log`.

---

## 🪵 Sample Logs

Real output from `logs/trades.log`, captured during actual testnet runs. Full files are in `logs_sample/`.

**Market order:**

```
2026-07-02 07:20:33,803 | INFO | Placing MARKET BUY order: symbol=BTCUSDT quantity=0.001
2026-07-02 07:20:34,605 | DEBUG | Request: POST /fapi/v1/order params={'symbol': 'BTCUSDT', 'side': 'BUY', 'type': 'MARKET', 'quantity': '0.001', 'timestamp': 1782957034605}
2026-07-02 07:20:34,892 | DEBUG | Response: status=200 body={'orderId': 18373207138, 'symbol': 'BTCUSDT', 'status': 'NEW', 'executedQty': '0.0000', 'type': 'MARKET', 'side': 'BUY', ...}
2026-07-02 07:20:34,892 | INFO | Order accepted: id=18373207138 executed_qty=0.0000 avg_price=None
```

**Limit order:**

```
2026-07-02 07:20:43,510 | INFO | Placing LIMIT BUY order: symbol=BTCUSDT quantity=0.001
2026-07-02 07:20:44,701 | DEBUG | Request: POST /fapi/v1/order params={'symbol': 'BTCUSDT', 'side': 'BUY', 'type': 'LIMIT', 'quantity': '0.001', 'price': '50000', 'timeInForce': 'GTC', 'timestamp': 1782957044701}
2026-07-02 07:20:44,892 | DEBUG | Response: status=200 body={'orderId': 18373222445, 'symbol': 'BTCUSDT', 'status': 'NEW', 'price': '50000.00', 'executedQty': '0.0000', 'type': 'LIMIT', ...}
2026-07-02 07:20:44,892 | INFO | Order accepted: id=18373222445 executed_qty=0.0000 avg_price=None
```

**TWAP order (bonus):**

```
2026-07-02 07:20:51,336 | INFO | Placing TWAP BUY order: symbol=BTCUSDT quantity=0.003
2026-07-02 07:20:51,964 | DEBUG | Request: POST /fapi/v1/order params={'symbol': 'BTCUSDT', 'side': 'BUY', 'type': 'MARKET', 'quantity': '0.001', 'timestamp': 1782957051964}
2026-07-02 07:20:52,147 | DEBUG | Response: status=200 body={'orderId': 18373244535, 'symbol': 'BTCUSDT', 'status': 'NEW', 'executedQty': '0.0000', 'type': 'MARKET', ...}
[... slices 2/3 + final TWAP summary — see logs_sample/twap_order_sample.log for the complete run]
```

All `executedQty`/`avgPrice` values reflect Binance's immediate order-acceptance response — see Assumptions below.

- Order output reflects Binance's immediate acceptance response, not settled fill state — `executedQty`/`avgPrice` may show `0`/`None` on orders that fill moments later. Polling `GET /order` for settlement was scoped out to stay within the time budget.
- TWAP slices are placed as MARKET orders (guarantees execution) and sequentially with blocking `time.sleep` — an async version would avoid blocking the calling thread.
- Retries apply only to network failures, never to API rejections (deterministic, so retrying wastes calls).
  **Next up if extended:** fill-settlement polling, async TWAP, OCO as a second bonus order type.

---

## 📝 Assumptions & Limitations

- Order output reflects Binance's immediate acceptance response, not settled fill state — `executedQty`/`avgPrice` may show `0`/`None` on orders that fill moments later. Polling `GET /order` for settlement was scoped out to stay within the time budget.
- TWAP slices are placed as MARKET orders (guarantees execution) and sequentially with blocking `time.sleep` — an async version would avoid blocking the calling thread.
- Retries apply only to network failures, never to API rejections (deterministic, so retrying wastes calls).

**Next up if extended:** fill-settlement polling, async TWAP, OCO as a second bonus order type.

---

## 🧪 Tests

```bash
pytest -v
```

**output**

```bash
================================================== test session starts ===================================================
platform win32 -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0 -- D:\Codes\assignments\trading_bot\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Codes\assignments\trading_bot
configfile: pyproject.toml
plugins: anyio-4.14.1, mock-3.15.1, respx-0.23.1
collected 11 items

tests/test_client.py::test_sign_adds_timestamp_and_signature PASSED                                                 [  9%]
tests/test_client.py::test_place_order_success PASSED                                                               [ 18%]
tests/test_client.py::test_place_order_insufficient_balance_raises PASSED                                           [ 27%]
tests/test_orders.py::test_market_order_execute PASSED                                                              [ 36%]
tests/test_orders.py::test_limit_order_execute PASSED                                                               [ 45%]
tests/test_orders.py::test_twap_order_execute_places_correct_slice_count PASSED                                     [ 54%]
tests/test_validators.py::test_market_order_valid PASSED                                                            [ 63%]
tests/test_validators.py::test_limit_order_requires_price PASSED                                                    [ 72%]
tests/test_validators.py::test_market_order_rejects_price PASSED                                                    [ 81%]
tests/test_validators.py::test_quantity_must_be_positive PASSED                                                     [ 90%]
tests/test_validators.py::test_twap_requires_slices_and_interval PASSED                                             [100%]

=================================================== 11 passed in 3.91s ===================================================
```

All tests mock the HTTP layer — no live credentials needed to run the suite.

---

## 👨‍💻 Author

> **Anvay Mayekar**
> 🎓 B.Tech in Electronics & Computer Science — SAKEC, Mumbai
>
> [![GitHub](https://img.shields.io/badge/GitHub-181717.svg?style=for-the-badge&logo=GitHub&logoColor=white)](https://www.github.com/anvaymayekar)
> [![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2.svg?style=for-the-badge&logo=LinkedIn&logoColor=white)](https://in.linkedin.com/in/anvaymayekar)
> [![Gmail](https://img.shields.io/badge/Gmail-D14836.svg?style=for-the-badge&logo=gmail&logoColor=white)](mailto:anvaay@gmail.com)
