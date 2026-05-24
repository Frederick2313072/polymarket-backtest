# polymarket-backtest

[![PyPI version](https://img.shields.io/pypi/v/polymarket-backtest.svg)](https://pypi.org/project/polymarket-backtest/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Downloads](https://img.shields.io/pypi/dm/polymarket-backtest.svg)](https://pypi.org/project/polymarket-backtest/)

**用于获取 Polymarket 赔率数据、评估预测市场交易策略的 Python 工具包。**

- 📡 **实时与历史赔率获取** — 通过 Polymarket 的 CLOB 和 Gamma API 拉取数据，无需鉴权
- 📦 **内置数据集** — 真实 BTC/ETH 15 分钟市场订单簿快照，开箱即用
- 📊 **回测指标** — 夏普比率、最大回撤、胜率、盈亏因子、卡玛比率
- 🧪 **统计计算** — Bootstrap 置信区间、假设检验（t / 二项 / Jarque-Bera）、Monte Carlo 路径模拟、Kelly 准则

```python
from polymarket_backtest.api import GammaClient, ClobClient
from polymarket_backtest.backtest import summary

# 获取 BTC 市场实时赔率
market = GammaClient().get_market_info("BTC")
df = ClobClient().get_price_history_df(market.up_token_id, interval="1d")

# 用内置数据集评估策略
from polymarket_backtest.data import load_trades
pnl = load_trades("flash_crash")["gross_pnl"].dropna().tolist()
print(summary(pnl))
# {'net_pnl': 47.92, 'win_rate': 0.143, 'sharpe_ratio': 0.145, 'max_drawdown': 14.51, ...}
```

---

## 什么是 Polymarket？

[Polymarket](https://polymarket.com) 是全球最大的预测市场平台。交易者买卖代表真实世界事件概率的份额，涵盖选举、加密货币价格等。每隔 15 分钟，新的 **BTC/ETH/SOL/XRP 涨跌** 市场开盘，形成透明链上结算的高频交易环境。

本库为你提供这些市场的编程访问接口，以及针对真实历史数据回测策略的工具。

---

## 安装

```bash
pip install polymarket-backtest
```

**依赖：** Python 3.10+，pandas、numpy、requests（自动安装）

---

## 功能特性

### 📡 API 客户端（无需 API Key）

| 客户端 | 数据源 | 获取内容 |
|--------|--------|----------|
| `GammaClient` | `gamma-api.polymarket.com` | 市场 slug、token ID、当前赔率、市场结束时间 |
| `ClobClient`  | `clob.polymarket.com`       | 任意 token 的历史价格时间序列 |

### 📦 内置数据集

来自 Polymarket 实盘 15 分钟加密货币市场的真实录制数据：

| 数据集 | 行数 | 描述 |
|--------|------|------|
| `btc_orderbook` | 13,749 | 跨多个 15 分钟周期的 BTC 涨/跌买卖价/中间价快照 |
| `flash_crash_trades` | 22 | Flash Crash 策略交易日志，含入场/出场价格与盈亏 |
| `flash_crash_summary` | — | 按币种和市场汇总的统计数据 |
| `hedge_arb_trades` | — | 对冲套利策略的双腿交易记录 |

### 📊 回测指标

所有指标均接受普通 Python `list[float]`（每笔交易盈亏）作为输入：

| 函数 | 描述 |
|------|------|
| `sharpe_ratio(pnl, periods_per_year=None)` | 可年化夏普比率 |
| `max_drawdown(pnl)` | 峰谷回撤（绝对值 + 百分比） |
| `win_rate(pnl)` | 盈利交易占比 |
| `profit_factor(pnl)` | 总盈利 / 总亏损 |
| `calmar_ratio(pnl)` | 净盈亏 / 最大回撤 |
| `summary(pnl)` | 以上所有指标汇总为一个字典 |
| `summary_from_df(df, pnl_col)` | 同上，但接受 DataFrame 列 |

### 🧪 统计计算

将统计计算课程的核心方法应用于策略评估，量化回测结果的**不确定性**——小样本（Polymarket 策略常常只有几十笔交易）下点估计极不稳定，必须配合区间估计和显著性检验。

| 函数 | 描述 |
|------|------|
| `bootstrap_sharpe_ci(pnl, n_bootstrap=1000, seed=None)` | 夏普比率的 Bootstrap 95% 置信区间（百分位法） |
| `bootstrap_win_rate_ci(pnl, ...)` | 胜率的 Bootstrap 置信区间 |
| `bootstrap_mean_ci(pnl, ...)` | 平均 PnL 的 Bootstrap 置信区间（不假设正态） |
| `bootstrap_ci(pnl, stat_fn, ...)` | 通用 Bootstrap CI，可对任意统计量计算 |
| `ttest_mean_zero(pnl, alternative="greater")` | 单样本 t 检验：平均 PnL 是否显著大于 0 |
| `binomial_test_win_rate(pnl, p0=0.5)` | 精确二项检验：胜率是否优于纯随机猜测 |
| `jarque_bera_test(pnl)` | 正态性检验（基于偏度 + 超额峰度） |
| `monte_carlo_paths(pnl, n_paths=1000, n_periods=100, seed=None)` | 基于历史 PnL 经验分布生成未来权益曲线 |
| `monte_carlo_summary(paths)` | 由模拟路径计算 VaR / CVaR / 回撤分布 |
| `kelly_fraction_from_pnl(pnl)` | 从历史 PnL 估计 Kelly 最优仓位 |

> `scipy` 为可选依赖：若已安装则使用 `scipy.stats` 的精确分布；否则自动回退到纯数值实现（Lentz 连分式计算 t 分布 CDF、卡方分布 CDF 闭式解、二项 PMF 直接求和），体现了统计计算课程中数值方法与理论分布的对应关系。

---

## 使用示例

### 获取当前市场信息

```python
from polymarket_backtest.api import GammaClient

client = GammaClient()

# 当前 BTC 活跃 15 分钟市场
market = client.get_market_info("BTC")
print(market.slug)         # "btc-updown-15m-1775035200"
print(market.up_price)     # 0.52（BTC 上涨概率 52%）
print(market.down_price)   # 0.48
print(market.end_date)     # "2025-04-01T03:30:00Z"

# 支持币种：BTC、ETH、SOL、XRP
# 列出最近 10 个市场
for m in client.list_recent_markets("ETH", n=10):
    print(m.slug, f"up={m.up_price:.2f} down={m.down_price:.2f}")
```

### 获取历史赔率（价格时间序列）

```python
from polymarket_backtest.api import GammaClient, ClobClient

gamma = GammaClient()
clob = ClobClient()

market = gamma.get_market_info("BTC")

# 返回 PricePoint 对象列表
history = clob.get_price_history(
    market.up_token_id,
    interval="1d",   # "1m" | "1h" | "6h" | "1d" | "1w" | "max"
    fidelity=60,     # 数据分辨率（分钟）
)
print(f"获取到 {len(history)} 个价格点")
# 获取到 24 个价格点

# 返回 pandas DataFrame（时间索引）
df = clob.get_price_history_df(market.up_token_id, interval="1w", fidelity=60)
print(df.tail())
#     timestamp   price                    datetime
# 165  1775016000  0.510  2025-03-31 20:00:00+00:00
# 166  1775019600  0.485  2025-03-31 21:00:00+00:00
# 167  1775023200  0.530  2025-03-31 22:00:00+00:00
```

### 使用内置数据集

```python
from polymarket_backtest.data import list_datasets, load_orderbook, load_trades

# 查看可用数据集
for ds in list_datasets():
    print(f"{ds['name']:25s} — {ds['description']}")

# BTC 订单簿快照（真实录制数据）
ob = load_orderbook("BTC")
print(ob[["recorded_at_ts", "up_bid", "up_ask", "down_bid", "remaining_seconds"]].head())
#    recorded_at_ts  up_bid  up_ask  down_bid  remaining_seconds
# 0  1775028136.217    0.02    0.03      0.97              463.0
# 1  1775028138.599    0.02    0.03      0.97              461.0

# 策略交易日志
trades = load_trades("flash_crash")
print(trades[["coin", "side", "exit_reason", "gross_pnl"]].head())
#   coin side    exit_reason  gross_pnl
# 0  BTC   up      stop_loss      -1.48
# 1  BTC down      stop_loss      -1.52
# 2  BTC   up  take_profit       +8.34
```

### 评估回测表现

```python
from polymarket_backtest.backtest import summary, sharpe_ratio, max_drawdown
from polymarket_backtest.data import load_trades

trades = load_trades("flash_crash")
pnl = trades["gross_pnl"].dropna().tolist()

# 一行汇总
result = summary(pnl)
print(result)
# {
#   'total_trades'    : 21,
#   'net_pnl'         : 47.92,
#   'avg_pnl'         : 2.28,
#   'std_pnl'         : 15.69,
#   'win_rate'        : 0.1429,     # 14.3% — 低胜率但高盈亏因子
#   'profit_factor'   : 2.5113,
#   'sharpe_ratio'    : 0.1454,
#   'max_drawdown'    : 14.51,
#   'max_drawdown_pct': 0.0,
#   'calmar_ratio'    : 3.30
# }

# 15 分钟市场年化夏普（每天 96 个市场 × 365 天）
print(sharpe_ratio(pnl, periods_per_year=35_040))

# 回撤详情
dd = max_drawdown(pnl)
print(f"最大回撤: ${dd['max_drawdown']:.2f}（第 {dd['peak_idx']} 笔交易达到峰值）")

# 直接从 DataFrame 列计算
from polymarket_backtest.backtest import summary_from_df
print(summary_from_df(trades, pnl_col="gross_pnl"))
```

### 量化不确定性（Bootstrap + 假设检验）

"夏普比率 = 0.14" 这种点估计在没有置信区间时几乎没有意义。仅 21 笔交易的样本下，真实夏普可能是 -1 也可能是 +0.5：

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

# 夏普比率的 95% Bootstrap 置信区间
print(bootstrap_sharpe_ci(pnl, n_bootstrap=2000, seed=42))
# {'point_estimate': 0.145, 'ci_lower': -1.36, 'ci_upper': 0.38, ...}
# CI 横跨 0 → 在统计意义上夏普与 0 不可区分

# 平均 PnL 是否显著大于 0？
print(ttest_mean_zero(pnl, alternative="greater"))
# {'t_stat': 0.67, 'p_value': 0.26, 'significant_at_5pct': False}

# 胜率是否优于抛硬币？
print(binomial_test_win_rate(pnl, p0=0.5, alternative="greater"))
# {'wins': 3, 'n_trades': 21, 'p_value': 0.9999, 'significant_at_5pct': False}

# 收益是否服从正态分布？（预测市场几乎从不正态）
print(jarque_bera_test(pnl))
# {'jb_stat': 261.4, 'skewness': 4.10, 'excess_kurtosis': 15.2, 'is_normal_at_5pct': False}
```

### Monte Carlo 权益曲线模拟

通过对历史 PnL 重采样，估计未来收益的整体分布——VaR、期望回撤、盈利概率：

```python
from polymarket_backtest.stats import monte_carlo_paths, monte_carlo_summary

# 模拟未来 50 笔交易的 2000 条权益曲线
paths = monte_carlo_paths(pnl, n_paths=2000, n_periods=50, seed=0)
print(paths.shape)        # (2000, 50)

print(monte_carlo_summary(paths))
# {
#   'final_mean'        : 114.26,   # 最终累计 PnL 均值
#   'final_median'      :  96.44,
#   'final_ci_lower'    : -65.05,   # 最终 PnL 的 2.5% 分位数
#   'final_ci_upper'    : 367.99,   # 最终 PnL 的 97.5% 分位数
#   'var_5pct'          : -53.51,   # 5% VaR：5% 的情况下亏损会比这更严重
#   'cvar_5pct'         : -66.79,   # 条件 VaR：最坏 5% 情形的期望亏损
#   'prob_profit'       : 0.889,    # 88.9% 的模拟路径最终盈利
#   'max_drawdown_mean' :  37.43,
#   'max_drawdown_p95'  :  65.88,   # 95% 的路径回撤不超过 $66
# }
```

### Kelly 准则：最优下注比例

给定估计的 edge，Kelly 准则给出最大化长期对数财富的最优仓位比例：

```python
from polymarket_backtest.stats import kelly_fraction, kelly_fraction_from_pnl

# 从交易日志自动估计
print(kelly_fraction_from_pnl(pnl))
# {
#   'kelly_fraction' : 0.086,    # 完整 Kelly：投入 8.6% 资本
#   'half_kelly'     : 0.043,    # 实务推荐（缓解参数估计误差）
#   'quarter_kelly'  : 0.021,
#   'win_rate'       : 0.143,
#   'avg_win'        : 26.54,
#   'avg_loss'       :  1.76,
#   'edge'           :  2.28,    # 单位资本的期望收益
# }

# 或者用已知参数直接计算
print(kelly_fraction(win_rate=0.6, avg_win=2.0, avg_loss=1.0))   # 0.40
```

> 警告：Kelly 对估计误差极其敏感。仅 20 余笔交易时，务必结合 `bootstrap_ci()` 评估 Kelly 比例的置信区间，实务中通常使用 half-Kelly 或 quarter-Kelly。

---

## 订单簿数据结构

`btc_orderbook` 数据集与 Polymarket WebSocket 实时推送结构一致：

| 字段 | 类型 | 描述 |
|------|------|------|
| `recorded_at_ts` | float | UNIX 时间戳（秒，UTC） |
| `market_slug` | str | 如 `"btc-updown-15m-1775027700"` |
| `up_bid` / `up_ask` / `up_mid` | float | 涨方向最优买价/卖价/中间价 |
| `down_bid` / `down_ask` / `down_mid` | float | 跌方向最优买价/卖价/中间价 |
| `remaining_seconds` | float | 距市场结算剩余秒数 |
| `elapsed_seconds` | float | 市场开盘后已过秒数 |

价格范围为 `[0, 1]`，表示隐含概率（如 `0.52` = 52% 概率）。

---

## 为什么选择本库？

大多数 Polymarket 工具专注于订单执行，本库专注于**研究与策略评估**：

- **无需 API Key** — Gamma API 和 CLOB 价格历史均为公开接口
- **零样板代码** — 市场发现、token ID 解析、DataFrame 转换一步完成
- **内置真实数据** — 无需等待数据积累即可开始回测
- **纯 Python 指标** — 无需可选 C 扩展，任意环境均可运行

---

## 路线图

- [ ] 多币种订单簿数据集（ETH、SOL、XRP）
- [ ] Gamma API 跨市场类型搜索（不限于 15 分钟加密货币）
- [ ] 滚动前向回测辅助工具
- [ ] 权益曲线绘图工具

---

## 贡献

欢迎提交 Pull Request！请先开 Issue 讨论较大的改动。

```bash
git clone https://github.com/yourname/polymarket-backtest
cd polymarket-backtest
pip install -e ".[dev]"
pytest
```

---

## 许可证

MIT © [Frederick](https://github.com/Frederick2313072)

---

> **免责声明：** 本库仅供研究和教育用途，不构成任何投资建议。预测市场交易存在亏损风险。
