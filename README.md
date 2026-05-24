# polymarket-backtest

[![PyPI version](https://img.shields.io/pypi/v/polymarket-backtest.svg)](https://pypi.org/project/polymarket-backtest/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Downloads](https://img.shields.io/pypi/dm/polymarket-backtest.svg)](https://pypi.org/project/polymarket-backtest/)

**A Python toolkit for fetching Polymarket odds data and evaluating prediction market trading strategies.**

- 📡 **Fetch live & historical odds** from Polymarket's CLOB and Gamma APIs — no auth required
- 📦 **Built-in datasets** — real BTC/ETH 15-minute market orderbook snapshots ready to use
- 📊 **Backtest metrics** — Sharpe ratio, max drawdown, win rate, profit factor, Calmar ratio
- 🧪 **Statistical computing** — Bootstrap confidence intervals, hypothesis testing (t / binomial / Jarque-Bera), Monte Carlo path simulation, Kelly criterion

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

### 🧪 Statistical Computing

Tools to quantify the *uncertainty* of your backtest results — because point estimates lie, especially with small samples (Polymarket strategies often produce <50 trades per study).

| Function | Description |
|----------|-------------|
| `bootstrap_sharpe_ci(pnl, n_bootstrap=1000, seed=None)` | Bootstrap 95% CI for Sharpe ratio (percentile method) |
| `bootstrap_win_rate_ci(pnl, ...)` | Bootstrap CI for win rate |
| `bootstrap_mean_ci(pnl, ...)` | Bootstrap CI for average PnL (no normality assumption) |
| `bootstrap_ci(pnl, stat_fn, ...)` | Generic Bootstrap CI for any statistic |
| `ttest_mean_zero(pnl, alternative="greater")` | One-sample t-test: is mean PnL significantly > 0? |
| `binomial_test_win_rate(pnl, p0=0.5)` | Exact binomial test: win rate vs. coin-flip baseline |
| `jarque_bera_test(pnl)` | Normality test (skewness + excess kurtosis) |
| `monte_carlo_paths(pnl, n_paths=1000, n_periods=100, seed=None)` | Simulate future equity curves by resampling history |
| `monte_carlo_summary(paths)` | VaR / CVaR / drawdown distribution from simulated paths |
| `kelly_fraction_from_pnl(pnl)` | Optimal bet size from estimated win rate & avg win/loss |

> `scipy` is an optional dependency — if installed, exact `scipy.stats` distributions are used; otherwise the module falls back to pure-numeric implementations (Lentz continued fractions for the t-CDF, closed-form chi-square CDF, direct PMF summation for the binomial test).

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

### Quantify uncertainty (Bootstrap + hypothesis tests)

Point estimates like "Sharpe = 0.14" are meaningless without a confidence interval. With only 21 trades, the *true* Sharpe could easily be -1 or +0.5:

```python
from polymarket_backtest.stats import (
    bootstrap_sharpe_ci,
    bootstrap_win_rate_ci,
    ttest_mean_zero,
    binomial_test_win_rate,
    jarque_bera_test,
)
from polymarket_backtest.data import load_trades

pnl = load_trades("flash_crash")["gross_pnl"].dropna().tolist()

# 95% bootstrap CI for the Sharpe ratio
print(bootstrap_sharpe_ci(pnl, n_bootstrap=2000, seed=42))
# {'point_estimate': 0.145, 'ci_lower': -1.36, 'ci_upper': 0.38, ...}
# CI straddles 0 → Sharpe is NOT statistically distinguishable from zero.

# Is the average PnL significantly greater than 0?
print(ttest_mean_zero(pnl, alternative="greater"))
# {'t_stat': 0.67, 'p_value': 0.26, 'significant_at_5pct': False}

# Is the win rate better than a coin flip?
print(binomial_test_win_rate(pnl, p0=0.5, alternative="greater"))
# {'wins': 3, 'n_trades': 21, 'p_value': 0.9999, 'significant_at_5pct': False}

# Are returns normally distributed? (Almost never for prediction markets.)
print(jarque_bera_test(pnl))
# {'jb_stat': 261.4, 'skewness': 4.10, 'excess_kurtosis': 15.2, 'is_normal_at_5pct': False}
```

### Monte Carlo equity-curve simulation

Resample historical PnL to estimate the distribution of future outcomes — Value-at-Risk, expected drawdown, probability of profit:

```python
from polymarket_backtest.stats import monte_carlo_paths, monte_carlo_summary

# Simulate 2000 possible equity curves over the next 50 trades
paths = monte_carlo_paths(pnl, n_paths=2000, n_periods=50, seed=0)
print(paths.shape)        # (2000, 50)

print(monte_carlo_summary(paths))
# {
#   'final_mean'        : 114.26,   # average ending PnL
#   'final_median'      :  96.44,
#   'final_ci_lower'    : -65.05,   # 2.5% percentile of final PnL
#   'final_ci_upper'    : 367.99,   # 97.5% percentile
#   'var_5pct'          : -53.51,   # 5% VaR — losses worse than this happen 5% of the time
#   'cvar_5pct'         : -66.79,   # expected loss in the worst 5% scenarios
#   'prob_profit'       : 0.889,    # 88.9% of simulated paths end positive
#   'max_drawdown_mean' :  37.43,
#   'max_drawdown_p95'  :  65.88,   # 95% of paths see drawdown ≤ $66
# }
```

### Kelly criterion: how much to bet

Given the estimated edge, the Kelly criterion gives the bet size that maximizes long-run log-wealth:

```python
from polymarket_backtest.stats import kelly_fraction, kelly_fraction_from_pnl

# Auto-estimate from the trade log
print(kelly_fraction_from_pnl(pnl))
# {
#   'kelly_fraction' : 0.086,    # full Kelly: bet 8.6% of capital
#   'half_kelly'     : 0.043,    # safer in practice (parameter uncertainty)
#   'quarter_kelly'  : 0.021,
#   'win_rate'       : 0.143,
#   'avg_win'        : 26.54,
#   'avg_loss'       :  1.76,
#   'edge'           :  2.28,    # expected PnL per unit capital
# }

# Or compute directly from known parameters
print(kelly_fraction(win_rate=0.6, avg_win=2.0, avg_loss=1.0))   # 0.40
```

> Warning: Kelly is very sensitive to estimation error. With only ~20 trades, always pair `kelly_fraction_from_pnl()` with `bootstrap_ci()` to see how wide the plausible range really is — and consider half- or quarter-Kelly in practice.

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
