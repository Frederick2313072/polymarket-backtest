r"""
Bootstrap 重采样与置信区间估计
==============================

Bootstrap 是统计计算课程中最具代表性的重采样方法之一。其核心思想：
当样本分布未知时，将经验分布作为总体分布的近似，通过有放回地反复重采样
得到任意统计量 \hat{\theta} 的近似抽样分布，进而构造置信区间。

适用场景：
    - 样本量小、无法假设正态性时（如本项目中 22 笔 Flash Crash 交易）
    - 待估统计量（如 Sharpe 比率、最大回撤）没有简单的解析方差公式

实现说明：
    - 使用 numpy 向量化采样（O(B·n) 复杂度）
    - 采用百分位法（Percentile Method）构造 CI，即对 B 个重采样统计量
      取经验分位数 [α/2, 1-α/2]
    - 支持设置随机种子保证可复现

参考课程内容：
    Efron & Tibshirani, "An Introduction to the Bootstrap" (1993)
"""

from __future__ import annotations

from typing import Callable, Sequence

import numpy as np

from ..backtest.metrics import sharpe_ratio, win_rate


__all__ = [
    "bootstrap_ci",
    "bootstrap_sharpe_ci",
    "bootstrap_win_rate_ci",
    "bootstrap_mean_ci",
]


def bootstrap_ci(
    pnl_series: Sequence[float],
    stat_fn: Callable[[Sequence[float]], float],
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
    seed: int | None = None,
) -> dict:
    """
    通用 Bootstrap 百分位置信区间。

    对原始样本有放回地重采样 ``n_bootstrap`` 次，每次计算统计量 ``stat_fn``，
    最终返回经验分布的关键分位数。

    参数：
        pnl_series: 原始样本（一维数值序列，如每笔交易 PnL）
        stat_fn: 任意统计量函数，签名为 f(samples) -> float
        n_bootstrap: 重采样次数 B（默认 1000；课程典型取值 1000-10000）
        confidence: 置信水平 1-α，默认 0.95
        seed: 随机种子，便于复现

    返回：
        dict 包含：
            point_estimate   原样本上的统计量值 theta_hat
            ci_lower         置信下界
            ci_upper         置信上界
            confidence       使用的置信水平
            n_bootstrap      实际重采样次数
            bootstrap_mean   B 次重采样统计量的均值
            bootstrap_std    B 次重采样统计量的标准差（theta_hat 的 SE 估计）

    示例：
        >>> import numpy as np
        >>> rng = np.random.default_rng(0)
        >>> pnl = rng.normal(0.5, 2.0, size=100).tolist()
        >>> bootstrap_ci(pnl, lambda x: float(np.mean(x)), seed=42)
        # {'point_estimate': 0.62, 'ci_lower': 0.21, 'ci_upper': 1.03, ...}
    """
    pnl = np.asarray(pnl_series, dtype=float)
    n = pnl.size

    if n == 0:
        return {
            "point_estimate": 0.0,
            "ci_lower": 0.0,
            "ci_upper": 0.0,
            "confidence": confidence,
            "n_bootstrap": 0,
            "bootstrap_mean": 0.0,
            "bootstrap_std": 0.0,
        }

    rng = np.random.default_rng(seed)
    # 一次性生成 B×n 的有放回索引矩阵，比循环快 10-100 倍
    idx = rng.integers(0, n, size=(n_bootstrap, n))
    resamples = pnl[idx]

    stats = np.empty(n_bootstrap, dtype=float)
    for b in range(n_bootstrap):
        stats[b] = float(stat_fn(resamples[b]))

    alpha = 1.0 - confidence
    lower_q = (alpha / 2.0) * 100.0
    upper_q = (1.0 - alpha / 2.0) * 100.0

    # 过滤 inf/nan：当样本全为正/全为负时，sharpe 可能返回 ±inf
    finite_stats = stats[np.isfinite(stats)]
    if finite_stats.size == 0:
        ci_lower = float("nan")
        ci_upper = float("nan")
        boot_mean = float("nan")
        boot_std = float("nan")
    else:
        ci_lower = float(np.percentile(finite_stats, lower_q))
        ci_upper = float(np.percentile(finite_stats, upper_q))
        boot_mean = float(np.mean(finite_stats))
        boot_std = float(np.std(finite_stats, ddof=1))

    return {
        "point_estimate": float(stat_fn(pnl)),
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "confidence": confidence,
        "n_bootstrap": n_bootstrap,
        "bootstrap_mean": boot_mean,
        "bootstrap_std": boot_std,
    }


def bootstrap_sharpe_ci(
    pnl_series: Sequence[float],
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
    periods_per_year: int | None = None,
    seed: int | None = None,
) -> dict:
    """
    Sharpe 比率的 Bootstrap 置信区间。

    Sharpe 比率没有简单的解析方差公式（取决于收益分布的高阶矩），
    Bootstrap 是估计其不确定性的标准方法。

    参数：
        pnl_series: 每笔交易盈亏序列
        n_bootstrap: 重采样次数
        confidence: 置信水平
        periods_per_year: 年化系数（与 sharpe_ratio() 一致）
        seed: 随机种子

    返回：
        dict，同 bootstrap_ci()。当 ci 跨过 0 时，说明 Sharpe 在统计意义上
        与 0 不可区分（策略未表现出显著的正风险调整收益）。
    """

    def _sharpe(x):
        return sharpe_ratio(list(x), periods_per_year=periods_per_year)

    return bootstrap_ci(
        pnl_series,
        stat_fn=_sharpe,
        n_bootstrap=n_bootstrap,
        confidence=confidence,
        seed=seed,
    )


def bootstrap_win_rate_ci(
    pnl_series: Sequence[float],
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
    seed: int | None = None,
) -> dict:
    """
    胜率的 Bootstrap 置信区间。

    虽然胜率有解析的二项分布 CI（见 ``hypothesis.binomial_test_win_rate``），
    Bootstrap CI 在小样本下更稳健，且与其他指标的 CI 计算方式保持一致。

    参数：
        pnl_series: 每笔交易盈亏序列
        n_bootstrap: 重采样次数
        confidence: 置信水平
        seed: 随机种子

    返回：
        dict，同 bootstrap_ci()。
    """
    return bootstrap_ci(
        pnl_series,
        stat_fn=lambda x: win_rate(list(x)),
        n_bootstrap=n_bootstrap,
        confidence=confidence,
        seed=seed,
    )


def bootstrap_mean_ci(
    pnl_series: Sequence[float],
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
    seed: int | None = None,
) -> dict:
    """
    平均 PnL 的 Bootstrap 置信区间。

    与经典 t 区间 ``mean ± t_{alpha/2} * s/sqrt(n)`` 相比，
    Bootstrap 不假设正态性，更适合 PnL 这种典型重尾分布。

    参数：
        pnl_series: 每笔交易盈亏序列
        n_bootstrap: 重采样次数
        confidence: 置信水平
        seed: 随机种子

    返回：
        dict，同 bootstrap_ci()。
    """
    return bootstrap_ci(
        pnl_series,
        stat_fn=lambda x: float(np.mean(x)),
        n_bootstrap=n_bootstrap,
        confidence=confidence,
        seed=seed,
    )
