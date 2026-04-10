"""
策略回测评估指标

提供标准量化金融指标，适用于 Polymarket 等预测市场的策略评估。

指标包括：
    - Sharpe Ratio（夏普比率）
    - Max Drawdown（最大回撤）
    - Win Rate（胜率）
    - Profit Factor（盈亏比）
    - Calmar Ratio（卡玛比率）
    - 综合 summary()

用法示例：
    from polymarket_backtest.backtest.metrics import summary, sharpe_ratio, max_drawdown
    from polymarket_backtest.data import load_trades

    trades = load_trades("flash_crash")
    pnl = trades["gross_pnl"].dropna().tolist()

    print(summary(pnl))
    # {'total_trades': 22, 'net_pnl': 47.9, 'win_rate': 0.14, 'sharpe_ratio': 0.85, ...}
"""

from __future__ import annotations

import math
from typing import Sequence


# ---------------------------------------------------------------------------
# 核心指标函数
# ---------------------------------------------------------------------------


def sharpe_ratio(
    pnl_series: Sequence[float],
    risk_free_rate: float = 0.0,
    periods_per_year: int | None = None,
) -> float:
    """
    计算夏普比率（Sharpe Ratio）。

    参数：
        pnl_series: 每笔交易的净盈亏序列（USDC）
        risk_free_rate: 无风险收益率（默认为 0）
        periods_per_year: 年化系数。
            - 传入 None（默认）：返回「每笔交易」维度的 Sharpe，不年化
            - 传入 35040（96 次/天 × 365 天）：按 15 分钟市场年化
            - 传入 252：按每日年化（标准做法）

    返回：
        Sharpe Ratio，无穷大时返回 inf（全部盈利无波动）

    公式：
        SR = (mean(r) - rf) / std(r)
        如果 periods_per_year 非空：SR_annual = SR × sqrt(periods_per_year)
    """
    n = len(pnl_series)
    if n == 0:
        return 0.0
    if n == 1:
        return float("inf") if pnl_series[0] > risk_free_rate else 0.0

    mean_r = _mean(pnl_series) - risk_free_rate
    std_r = _std(pnl_series)

    if std_r == 0:
        return float("inf") if mean_r > 0 else (float("-inf") if mean_r < 0 else 0.0)

    sr = mean_r / std_r
    if periods_per_year is not None:
        sr *= math.sqrt(periods_per_year)
    return sr


def max_drawdown(pnl_series: Sequence[float]) -> dict:
    """
    计算最大回撤（Max Drawdown）。

    从累积 PnL 曲线中找到最大「峰到谷」跌幅。

    参数：
        pnl_series: 每笔交易的净盈亏序列（按时间顺序）

    返回：
        dict 包含：
            max_drawdown      最大回撤金额（非负，0 表示无回撤）
            max_drawdown_pct  相对回撤百分比（相对于峰值）
            peak_idx          峰值位置（在累积 PnL 数组中的索引）
            trough_idx        谷值位置
            peak_value        峰值累积 PnL
            trough_value      谷值累积 PnL
    """
    if not pnl_series:
        return {
            "max_drawdown": 0.0,
            "max_drawdown_pct": 0.0,
            "peak_idx": 0,
            "trough_idx": 0,
            "peak_value": 0.0,
            "trough_value": 0.0,
        }

    # 构建累积 PnL（从 0 开始）
    cumulative = [0.0]
    running = 0.0
    for p in pnl_series:
        running += p
        cumulative.append(running)

    peak = cumulative[0]
    peak_idx = 0
    max_dd = 0.0
    best_peak_idx = 0
    best_trough_idx = 0
    best_peak_val = 0.0
    best_trough_val = 0.0

    for i, val in enumerate(cumulative):
        if val > peak:
            peak = val
            peak_idx = i
        dd = peak - val
        if dd > max_dd:
            max_dd = dd
            best_peak_idx = peak_idx
            best_trough_idx = i
            best_peak_val = peak
            best_trough_val = val

    max_dd_pct = (max_dd / best_peak_val * 100) if best_peak_val > 0 else 0.0

    return {
        "max_drawdown": max_dd,
        "max_drawdown_pct": max_dd_pct,
        "peak_idx": best_peak_idx,
        "trough_idx": best_trough_idx,
        "peak_value": best_peak_val,
        "trough_value": best_trough_val,
    }


def win_rate(pnl_series: Sequence[float]) -> float:
    """
    计算胜率（Win Rate）。

    pnl > 0 视为盈利（胜），pnl <= 0 视为亏损（败）。

    参数：
        pnl_series: 每笔交易的净盈亏序列

    返回：
        胜率 [0.0, 1.0]，空序列返回 0.0
    """
    if not pnl_series:
        return 0.0
    wins = sum(1 for p in pnl_series if p > 0)
    return wins / len(pnl_series)


def profit_factor(pnl_series: Sequence[float]) -> float:
    """
    计算盈亏比（Profit Factor）。

    定义为：总盈利 / |总亏损|。
    大于 1 表示整体盈利，等于 inf 表示从未亏损。

    参数：
        pnl_series: 每笔交易的净盈亏序列

    返回：
        盈亏比（>= 0），无亏损时返回 inf
    """
    gross_profit = sum(p for p in pnl_series if p > 0)
    gross_loss = abs(sum(p for p in pnl_series if p < 0))
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def calmar_ratio(pnl_series: Sequence[float]) -> float:
    """
    计算卡玛比率（Calmar Ratio）。

    定义为：总净利 / 最大回撤。衡量收益与最大亏损的性价比。

    参数：
        pnl_series: 每笔交易的净盈亏序列

    返回：
        卡玛比率，无回撤时返回 inf
    """
    dd_info = max_drawdown(pnl_series)
    mdd = dd_info["max_drawdown"]
    net = sum(pnl_series)
    if mdd == 0:
        return float("inf") if net > 0 else 0.0
    return net / mdd


def summary(
    pnl_series: Sequence[float],
    periods_per_year: int | None = None,
) -> dict:
    """
    综合回测统计摘要。

    参数：
        pnl_series: 每笔交易的净盈亏序列（USDC）
        periods_per_year: 年化系数（同 sharpe_ratio）

    返回：
        dict 包含所有关键指标：
            total_trades      交易笔数
            net_pnl           净盈亏
            avg_pnl           平均单笔盈亏
            std_pnl           盈亏标准差
            win_rate          胜率 [0, 1]
            profit_factor     盈亏比
            sharpe_ratio      夏普比率
            max_drawdown      最大回撤（金额）
            max_drawdown_pct  最大回撤（百分比）
            calmar_ratio      卡玛比率

    示例：
        >>> pnl = [2.5, -1.0, 3.2, -0.5, 1.8]
        >>> summary(pnl)
        {'total_trades': 5, 'net_pnl': 6.0, 'avg_pnl': 1.2, ..., 'win_rate': 0.6, ...}
    """
    pnl = list(pnl_series)
    dd = max_drawdown(pnl)

    return {
        "total_trades": len(pnl),
        "net_pnl": round(sum(pnl), 4),
        "avg_pnl": round(_mean(pnl), 4) if pnl else 0.0,
        "std_pnl": round(_std(pnl), 4) if len(pnl) > 1 else 0.0,
        "win_rate": round(win_rate(pnl), 4),
        "profit_factor": round(profit_factor(pnl), 4),
        "sharpe_ratio": round(sharpe_ratio(pnl, periods_per_year=periods_per_year), 4),
        "max_drawdown": round(dd["max_drawdown"], 4),
        "max_drawdown_pct": round(dd["max_drawdown_pct"], 2),
        "calmar_ratio": round(calmar_ratio(pnl), 4),
    }


# ---------------------------------------------------------------------------
# 便捷函数：直接从 DataFrame 计算
# ---------------------------------------------------------------------------


def summary_from_df(df, pnl_col: str = "net_pnl", periods_per_year: int | None = None) -> dict:
    """
    直接从 pandas DataFrame 计算回测摘要。

    参数：
        df: 包含 PnL 列的 DataFrame（来自 load_trades() 等）
        pnl_col: PnL 列名（默认 "net_pnl"，flash_crash 策略用 "gross_pnl"）
        periods_per_year: 年化系数

    返回：
        同 summary() 的 dict
    """
    series = df[pnl_col].dropna().tolist()
    return summary(series, periods_per_year=periods_per_year)


# ---------------------------------------------------------------------------
# 内部工具函数（不依赖 numpy，纯标准库）
# ---------------------------------------------------------------------------


def _mean(xs: Sequence[float]) -> float:
    if not xs:
        return 0.0
    return sum(xs) / len(xs)


def _std(xs: Sequence[float], ddof: int = 1) -> float:
    n = len(xs)
    if n <= ddof:
        return 0.0
    m = _mean(xs)
    variance = sum((x - m) ** 2 for x in xs) / (n - ddof)
    return math.sqrt(variance)
