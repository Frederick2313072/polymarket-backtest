"""
Monte Carlo 模拟与 Kelly 准则
============================

Monte Carlo 方法是统计计算课程的核心内容之一：当解析解难以求得时，
通过大量随机模拟近似目标分布。本模块给出两类应用：

    1. 权益曲线模拟：用历史 PnL 经验分布作为总体，生成未来 N 期的
       可能轨迹，得到最终收益的分布、VaR / CVaR、最大回撤分布。
    2. Kelly 仓位求解：在已知胜率 p、盈亏比 b 的情况下，
       Kelly 准则给出最大化长期对数财富的最优下注比例 f*。

依赖：numpy（向量化批量模拟）
"""

from __future__ import annotations

from typing import Sequence

import numpy as np


__all__ = [
    "monte_carlo_paths",
    "monte_carlo_summary",
    "kelly_fraction",
    "kelly_fraction_from_pnl",
]


# ---------------------------------------------------------------------------
# Monte Carlo 路径模拟
# ---------------------------------------------------------------------------


def monte_carlo_paths(
    pnl_series: Sequence[float],
    n_paths: int = 1000,
    n_periods: int | None = None,
    seed: int | None = None,
) -> np.ndarray:
    """
    从历史 PnL 经验分布生成 Monte Carlo 权益曲线。

    每条路径：对原始 PnL 序列有放回地采样 ``n_periods`` 次，再做累加和。
    这等价于假设未来收益从历史经验分布 i.i.d. 抽取——是统计计算课程中
    "经验自助法（empirical Bootstrap）应用于时间序列"的最简形式。

    参数：
        pnl_series: 历史每笔 PnL（一维数值）
        n_paths: 模拟路径数（默认 1000）
        n_periods: 每条路径长度。None 表示与原序列等长
        seed: 随机种子

    返回：
        numpy.ndarray，形状为 ``(n_paths, n_periods)``，每行是一条累计 PnL 曲线
        （从 0 开始的累加和）。

    示例：
        >>> paths = monte_carlo_paths([1, -2, 3, -1], n_paths=500, n_periods=20, seed=0)
        >>> paths.shape
        (500, 20)
        >>> paths[:, -1].mean()   # 平均最终累计 PnL
    """
    pnl = np.asarray(pnl_series, dtype=float)
    if pnl.size == 0:
        return np.zeros((n_paths, 0))

    if n_periods is None:
        n_periods = pnl.size

    rng = np.random.default_rng(seed)
    samples = rng.choice(pnl, size=(n_paths, n_periods), replace=True)
    return np.cumsum(samples, axis=1)


def monte_carlo_summary(
    paths: np.ndarray,
    confidence: float = 0.95,
) -> dict:
    """
    汇总 Monte Carlo 路径的统计特征。

    参数：
        paths: monte_carlo_paths() 的输出（n_paths × n_periods 累计 PnL 矩阵）
        confidence: VaR 的置信水平（默认 0.95，即报告 5% / 95% 分位数）

    返回：
        dict，关键字段：
            n_paths            模拟路径数
            n_periods          每条路径长度
            final_mean         最终累计 PnL 的均值
            final_median       最终累计 PnL 的中位数
            final_std          最终累计 PnL 的标准差
            final_ci_lower     最终 PnL 的下分位数（默认 2.5%）
            final_ci_upper     最终 PnL 的上分位数（默认 97.5%）
            var_5pct           最终 PnL 的 5% 分位数（VaR_{0.95} 的传统定义）
            cvar_5pct          条件 VaR：所有低于 5% 分位数路径的均值（期望损失）
            prob_profit        最终 PnL 为正的路径比例
            max_drawdown_mean  路径内最大回撤的均值
            max_drawdown_p95   路径内最大回撤的 95% 分位数（最坏 5% 情形）
    """
    if paths.size == 0 or paths.shape[1] == 0:
        return {
            "n_paths": int(paths.shape[0]) if paths.ndim == 2 else 0,
            "n_periods": 0,
            "final_mean": 0.0,
            "final_median": 0.0,
            "final_std": 0.0,
            "final_ci_lower": 0.0,
            "final_ci_upper": 0.0,
            "var_5pct": 0.0,
            "cvar_5pct": 0.0,
            "prob_profit": 0.0,
            "max_drawdown_mean": 0.0,
            "max_drawdown_p95": 0.0,
        }

    n_paths, n_periods = paths.shape
    finals = paths[:, -1]
    alpha = 1.0 - confidence
    lower_q = (alpha / 2.0) * 100.0
    upper_q = (1.0 - alpha / 2.0) * 100.0

    var_threshold = float(np.percentile(finals, 5.0))
    tail_mask = finals <= var_threshold
    cvar = float(finals[tail_mask].mean()) if tail_mask.any() else var_threshold

    # 沿时间方向计算每条路径的运行最大值和回撤
    # 把"起点 0"加进去，模拟从空仓开始的情形
    full = np.concatenate([np.zeros((n_paths, 1)), paths], axis=1)
    running_max = np.maximum.accumulate(full, axis=1)
    drawdowns = running_max - full
    max_dd_per_path = drawdowns.max(axis=1)

    return {
        "n_paths": int(n_paths),
        "n_periods": int(n_periods),
        "final_mean": float(finals.mean()),
        "final_median": float(np.median(finals)),
        "final_std": float(finals.std(ddof=1)) if n_paths > 1 else 0.0,
        "final_ci_lower": float(np.percentile(finals, lower_q)),
        "final_ci_upper": float(np.percentile(finals, upper_q)),
        "var_5pct": var_threshold,
        "cvar_5pct": cvar,
        "prob_profit": float((finals > 0).mean()),
        "max_drawdown_mean": float(max_dd_per_path.mean()),
        "max_drawdown_p95": float(np.percentile(max_dd_per_path, 95.0)),
    }


# ---------------------------------------------------------------------------
# Kelly 准则
# ---------------------------------------------------------------------------


def kelly_fraction(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """
    Kelly 准则最优下注比例。

    公式：
        f* = (p * b - q) / b
        其中
            p = 胜率
            q = 1 - p
            b = 平均盈利 / |平均亏损|（赔率，Edge-to-Odds 比）

    解释：
        - f* > 0  ⇒ 策略有正期望，应该投入 f* 比例的资本
        - f* <= 0 ⇒ 策略无正期望，不应下注
        - 实务中通常使用 "分数 Kelly"（如 0.25 * f*），因为完整 Kelly
          对参数估计误差极其敏感（小样本下高估 edge 会导致灾难性回撤）。

    参数：
        win_rate: 胜率 p ∈ [0, 1]
        avg_win:  平均盈利金额（应 > 0）
        avg_loss: 平均亏损金额（取正数，函数内部自动取绝对值）

    返回：
        Kelly 比例 f*。当 avg_loss 为 0 时：
            - 若有盈利交易：返回 1.0（满仓，因为没有亏损风险）
            - 否则：返回 0.0
    """
    if not 0.0 <= win_rate <= 1.0:
        raise ValueError(f"win_rate must be in [0, 1], got {win_rate}")

    loss = abs(avg_loss)
    if loss == 0.0:
        return 1.0 if avg_win > 0 else 0.0

    if avg_win <= 0.0:
        return 0.0

    b = avg_win / loss
    p = win_rate
    q = 1.0 - p
    return (p * b - q) / b


def kelly_fraction_from_pnl(pnl_series: Sequence[float]) -> dict:
    """
    从历史 PnL 序列直接估计 Kelly 比例。

    自动从样本中估计：
        - 胜率 = #{PnL > 0} / n
        - 平均盈利 = mean(PnL | PnL > 0)
        - 平均亏损 = mean(|PnL| | PnL < 0)

    参数：
        pnl_series: 每笔交易 PnL 序列

    返回：
        dict 包含：
            kelly_fraction      完整 Kelly 比例 f*
            half_kelly          0.5 * f*（更稳健的实务推荐）
            quarter_kelly       0.25 * f*（保守版）
            win_rate            估计胜率
            avg_win             估计平均盈利
            avg_loss            估计平均亏损（取正数）
            edge                p * avg_win - (1-p) * avg_loss（单位资本期望收益）

    警告：
        小样本（如 22 笔交易）下 Kelly 估计的标准误极大，应结合
        bootstrap_ci 评估其不确定性后再用于实盘。
    """
    pnl = np.asarray(pnl_series, dtype=float)
    n = pnl.size
    if n == 0:
        return {
            "kelly_fraction": 0.0,
            "half_kelly": 0.0,
            "quarter_kelly": 0.0,
            "win_rate": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "edge": 0.0,
        }

    wins_mask = pnl > 0
    losses_mask = pnl < 0
    n_wins = int(wins_mask.sum())
    n_losses = int(losses_mask.sum())

    p = n_wins / n
    avg_win = float(pnl[wins_mask].mean()) if n_wins > 0 else 0.0
    avg_loss = float(-pnl[losses_mask].mean()) if n_losses > 0 else 0.0

    f_star = kelly_fraction(p, avg_win, avg_loss)
    edge = p * avg_win - (1.0 - p) * avg_loss

    return {
        "kelly_fraction": f_star,
        "half_kelly": f_star * 0.5,
        "quarter_kelly": f_star * 0.25,
        "win_rate": p,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "edge": edge,
    }
