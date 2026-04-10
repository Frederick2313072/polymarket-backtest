# polymarket-backtest

[![PyPI version](https://img.shields.io/pypi/v/polymarket-backtest.svg)](https://pypi.org/project/polymarket-backtest/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Downloads](https://img.shields.io/pypi/dm/polymarket-backtest.svg)](https://pypi.org/project/polymarket-backtest/)

**A Python toolkit for fetching Polymarket odds data and evaluating prediction market trading strategies.**

- 📡 **Fetch live & historical odds** from Polymarket's CLOB and Gamma APIs — no auth required
- 📦 **Built-in datasets** — real BTC/ETH 15-minute market orderbook snapshots ready to use
- 📊 **Backtest metrics** — Sharpe ratio, max drawdown, win rate, profit factor, Calmar ratio

```python
from polymarket_backtest.api import GammaClient, ClobClient
from polymarket_backtest.backtest import summary

# Get live BTC market odds
market = GammaClient().get_market_info("BTC")
df = ClobClient().get_price_history_df(market.up_token_id, interval="1d")

# Evaluate a strategy on built-in data
from polymarket_backtest.data import load_trades
pnl = load_trades("flash_crash")["gross_pnl"].dropna().tolist()
print(summary(pnl))
# {'net_pnl': 47.92, 'win_rate': 0.143, 'sharpe_ratio': 0.145, 'max_drawdown': 14.51, ...}
```

---

## What is Polymarket?

[Polymarket](https://polymarket.com) is the world's largest prediction market platform. Traders buy and sell shares representing the probability of real-world events — from elections to crypto prices. Every 15 minutes, new **BTC/ETH/SOL/XRP Up or Down** markets open, creating a high-frequency trading environment with transparent on-chain settlement.

This library gives you programmatic access to those markets and the tools to backtest strategies against real historical data.

---

## Installation

```bash
pip install polymarket-backtest
```

**Requirements:** Python 3.10+, pandas, numpy, requests (auto-installed)

---

## Features

### 📡 API Clients (no API key needed)

| Client | Source | What you get |
|--------|--------|--------------|
| `GammaClient` | `gamma-api.polymarket.com` | Market slugs, token IDs, current odds, market end times |
| `ClobClient`  | `clob.polymarket.com`       | Historical price time series for any token |

### 📦 Built-in Datasets

Real data recorded from Polymarket's live 15-minute crypto markets:

| Dataset | Rows | Description |
|---------|------|-------------|
| `btc_orderbook` | 13,749 | BTC UP/DOWN bid/ask/mid snapshots across multiple 15-min periods |
| `flash_crash_trades` | 22 | Flash Crash strategy trade log with entry/exit prices and PnL |
| `flash_crash_summary` | — | Aggregated stats by coin and market |
| `hedge_arb_trades` | — | Hedge Arbitrage strategy two-leg trade records |

### 📊 Backtest Metrics

All metrics work on a plain Python `list[float]` of per-trade PnL:

| Function | Description |
|----------|-------------|
| `sharpe_ratio(pnl, periods_per_year=None)` | Annualizable Sharpe ratio |
| `max_drawdown(pnl)` | Peak-to-trough drawdown (absolute + %) |
| `win_rate(pnl)` | Fraction of profitable trades |
| `profit_factor(pnl)` | Gross profit / gross loss |
| `calmar_ratio(pnl)` | Net PnL / max drawdown |
| `summary(pnl)` | All of the above in one dict |
| `summary_from_df(df, pnl_col)` | Same, but takes a DataFrame column |

---

## Usage

### Fetch current market info

```python
from polymarket_backtest.api import GammaClient

client = GammaClient()

# Current active 15-minute market for BTC
market = client.get_market_info("BTC")
print(market.slug)         # "btc-updown-15m-1775035200"
print(market.up_price)     # 0.52  (52% chance BTC goes up)
print(market.down_price)   # 0.48
print(market.end_date)     # "2025-04-01T03:30:00Z"

# Supported coins: BTC, ETH, SOL, XRP
# List the last 10 markets
for m in client.list_recent_markets("ETH", n=10):
    print(m.slug, f"up={m.up_price:.2f} down={m.down_price:.2f}")
```

### Fetch historical odds (price time series)

```python
from polymarket_backtest.api import GammaClient, ClobClient

gamma = GammaClient()
clob = ClobClient()

market = gamma.get_market_info("BTC")

# As a list of PricePoint objects
history = clob.get_price_history(
    market.up_token_id,
    interval="1d",   # "1m" | "1h" | "6h" | "1d" | "1w" | "max"
    fidelity=60,     # data resolution in minutes
)
print(f"Got {len(history)} price points")
# Got 24 price points

# As a pandas DataFrame (datetime-indexed)
df = clob.get_price_history_df(market.up_token_id, interval="1w", fidelity=60)
print(df.tail())
#     timestamp   price                    datetime
# 165  1775016000  0.510  2025-03-31 20:00:00+00:00
# 166  1775019600  0.485  2025-03-31 21:00:00+00:00
# 167  1775023200  0.530  2025-03-31 22:00:00+00:00
```

### Work with built-in datasets

```python
from polymarket_backtest.data import list_datasets, load_orderbook, load_trades

# See what's available
for ds in list_datasets():
    print(f"{ds['name']:25s} — {ds['description']}")

# BTC orderbook snapshots (real recorded data)
ob = load_orderbook("BTC")
print(ob[["recorded_at_ts", "up_bid", "up_ask", "down_bid", "remaining_seconds"]].head())
#    recorded_at_ts  up_bid  up_ask  down_bid  remaining_seconds
# 0  1775028136.217    0.02    0.03      0.97              463.0
# 1  1775028138.599    0.02    0.03      0.97              461.0

# Strategy trade logs
trades = load_trades("flash_crash")
print(trades[["coin", "side", "exit_reason", "gross_pnl"]].head())
#   coin side    exit_reason  gross_pnl
# 0  BTC   up      stop_loss      -1.48
# 1  BTC down      stop_loss      -1.52
# 2  BTC   up  take_profit       +8.34
```

### Evaluate backtest performance

```python
from polymarket_backtest.backtest import summary, sharpe_ratio, max_drawdown
from polymarket_backtest.data import load_trades

trades = load_trades("flash_crash")
pnl = trades["gross_pnl"].dropna().tolist()

# One-liner summary
result = summary(pnl)
print(result)
# {
#   'total_trades'   : 21,
#   'net_pnl'        : 47.92,
#   'avg_pnl'        : 2.28,
#   'std_pnl'        : 15.69,
#   'win_rate'       : 0.1429,     # 14.3% — low win rate but high profit factor
#   'profit_factor'  : 2.5113,
#   'sharpe_ratio'   : 0.1454,
#   'max_drawdown'   : 14.51,
#   'max_drawdown_pct': 0.0,
#   'calmar_ratio'   : 3.30
# }

# Annualized Sharpe for 15-minute markets (96 markets/day × 365 days)
print(sharpe_ratio(pnl, periods_per_year=35_040))

# Drawdown details
dd = max_drawdown(pnl)
print(f"Max drawdown: ${dd['max_drawdown']:.2f} (peak at trade #{dd['peak_idx']})")

# Directly from a DataFrame column
from polymarket_backtest.backtest import summary_from_df
print(summary_from_df(trades, pnl_col="gross_pnl"))
```

---

## Orderbook Data Schema

The `btc_orderbook` dataset mirrors what Polymarket's WebSocket streams in real time:

| Column | Type | Description |
|--------|------|-------------|
| `recorded_at_ts` | float | UNIX timestamp (seconds, UTC) |
| `market_slug` | str | e.g. `"btc-updown-15m-1775027700"` |
| `up_bid` / `up_ask` / `up_mid` | float | Best bid/ask/mid for the UP outcome |
| `down_bid` / `down_ask` / `down_mid` | float | Best bid/ask/mid for the DOWN outcome |
| `remaining_seconds` | float | Seconds until market settlement |
| `elapsed_seconds` | float | Seconds since market open |

Prices are in the range `[0, 1]` representing probability (e.g. `0.52` = 52% implied probability).

---

## Why use this library?

Most Polymarket tools focus on order execution. This library focuses on **research and strategy evaluation**:

- **No API key needed** for data fetching — Gamma API and CLOB price history are public
- **Zero boilerplate** — market discovery, token ID resolution, and DataFrame conversion in one call
- **Real recorded data included** — stop waiting to collect enough data to start backtesting
- **Pure Python metrics** — no optional C extensions; works in any environment

---

## Roadmap

- [ ] Multi-coin orderbook datasets (ETH, SOL, XRP)
- [ ] Gamma API search across all market types (not just 15-min crypto)
- [ ] Walk-forward backtesting helper
- [ ] Equity curve plotting utilities

---

## Contributing

Pull requests are welcome! Please open an issue first to discuss major changes.

```bash
git clone https://github.com/yourname/polymarket-backtest
cd polymarket-backtest
pip install -e ".[dev]"
pytest
```

---

## License

MIT © [Frederick](https://github.com/Frederick2313072)

---

> **Disclaimer:** This library is for research and educational purposes. It does not constitute financial advice. Prediction market trading involves risk of loss.
