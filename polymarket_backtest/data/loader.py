"""
内置示例数据集加载器

提供对项目内置回测数据集的访问。数据来自 Polymarket BTC/ETH 15 分钟市场的
真实盘口快照记录，可直接用于策略回测或分析演示。

用法示例：
    from polymarket_backtest.data import list_datasets, load_orderbook, load_trades

    # 查看可用数据集
    print(list_datasets())

    # 加载 BTC 盘口快照
    df = load_orderbook("BTC")
    print(df.head())

    # 加载 Flash Crash 策略回测记录
    trades = load_trades("flash_crash")
    print(trades[["coin", "side", "gross_pnl", "exit_reason"]].head())
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

_SAMPLE_DIR = Path(__file__).parent / "sample"

# 数据集名称 → 文件名 映射
_DATASETS: dict[str, dict] = {
    "btc_orderbook": {
        "file": "btc_orderbook.csv",
        "description": "BTC 15 分钟市场盘口快照（~13750 行），含 UP/DOWN 双向 bid/ask/mid",
    },
    "flash_crash_trades": {
        "file": "flash_crash_trades.csv",
        "description": "Flash Crash 策略逐笔交易记录，含入场/出场价格及 PnL",
    },
    "flash_crash_summary": {
        "file": "flash_crash_summary.csv",
        "description": "Flash Crash 策略回测汇总，含胜率、总 PnL 等统计指标",
    },
    "hedge_arb_trades": {
        "file": "hedge_arb_trades.csv",
        "description": "Hedge Arbitrage 策略逐笔交易记录，含双腿成交及净 PnL",
    },
}


def list_datasets() -> list[dict]:
    """
    列出所有可用内置数据集。

    返回：
        list of dict，每项包含 name、file、description
    """
    return [{"name": name, **meta} for name, meta in _DATASETS.items()]


def load_dataset(name: str) -> pd.DataFrame:
    """
    按名称加载内置数据集。

    参数：
        name: 数据集名称（使用 list_datasets() 查看可用值）

    返回：
        pandas DataFrame
    """
    if name not in _DATASETS:
        available = list(_DATASETS.keys())
        raise ValueError(f"未知数据集: {name!r}。可用: {available}")
    file_path = _SAMPLE_DIR / _DATASETS[name]["file"]
    return pd.read_csv(file_path)


def load_orderbook(coin: str = "BTC") -> pd.DataFrame:
    """
    加载内置盘口快照数据集。

    目前仅内置 BTC 数据。列包括：
        recorded_at_ts, coin, market_slug,
        up_bid, up_ask, up_mid, down_bid, down_ask, down_mid,
        remaining_seconds, elapsed_seconds, ...

    参数：
        coin: 币种（当前仅支持 "BTC"）

    返回：
        pandas DataFrame
    """
    if coin.upper() != "BTC":
        raise ValueError(f"内置盘口数据目前仅支持 BTC，暂不支持 {coin!r}")
    return load_dataset("btc_orderbook")


def load_trades(strategy: str) -> pd.DataFrame:
    """
    加载内置回测逐笔交易记录。

    参数：
        strategy: 策略名称，可选：
            - "flash_crash"  Flash Crash 策略
            - "hedge_arb"    Hedge Arbitrage 策略

    返回：
        pandas DataFrame，含每笔交易的进出场详情与 PnL
    """
    mapping = {
        "flash_crash": "flash_crash_trades",
        "hedge_arb": "hedge_arb_trades",
    }
    key = strategy.lower()
    if key not in mapping:
        raise ValueError(f"未知策略: {strategy!r}。可选: {list(mapping.keys())}")
    return load_dataset(mapping[key])


def load_summary(strategy: str = "flash_crash") -> pd.DataFrame:
    """
    加载内置回测汇总统计。

    参数：
        strategy: 策略名称（目前支持 "flash_crash"）

    返回：
        pandas DataFrame，含胜率、PnL 等汇总指标
    """
    mapping = {
        "flash_crash": "flash_crash_summary",
    }
    key = strategy.lower()
    if key not in mapping:
        raise ValueError(f"汇总数据目前仅支持: {list(mapping.keys())}")
    return load_dataset(mapping[key])
