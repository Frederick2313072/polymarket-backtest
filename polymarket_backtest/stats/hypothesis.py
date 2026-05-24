"""
假设检验
========

为策略回测提供统计显著性检验，避免被小样本的偶然结果欺骗。

包含三类经典检验：
    1. 单样本 t 检验：平均 PnL 是否显著非零（参数检验）
    2. 二项检验：胜率是否显著高于随机猜测（精确检验）
    3. Jarque-Bera 检验：收益分布是否服从正态（拟合优度检验）

软依赖设计：
    若安装了 scipy，会自动调用 ``scipy.stats`` 中的精确实现；
    否则使用纯数值方法（直接对分布函数做数值积分或求和），
    保证零依赖下也能跑出合理结果。这种"双轨制"是统计计算课程
    展示数值方法与理论分布关系的常见做法。
"""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np

try:
    from scipy import stats as _scipy_stats  # type: ignore

    _HAS_SCIPY = True
except ImportError:
    _scipy_stats = None
    _HAS_SCIPY = False


__all__ = [
    "ttest_mean_zero",
    "binomial_test_win_rate",
    "jarque_bera_test",
    "has_scipy",
]


def has_scipy() -> bool:
    """返回 scipy 是否可用。"""
    return _HAS_SCIPY


# ---------------------------------------------------------------------------
# 1. 单样本 t 检验
# ---------------------------------------------------------------------------


def ttest_mean_zero(
    pnl_series: Sequence[float],
    mu0: float = 0.0,
    alternative: str = "two-sided",
) -> dict:
    """
    单样本 t 检验：检验平均 PnL 是否显著不等于 ``mu0``。

    假设：
        H0: E[PnL] = mu0
        H1: E[PnL] != mu0   (alternative="two-sided")
            E[PnL] >  mu0   (alternative="greater")
            E[PnL] <  mu0   (alternative="less")

    统计量：
        t = (\bar{x} - mu0) / (s / sqrt(n))      ~  t(n-1)  在 H0 下

    参数：
        pnl_series: 每笔交易盈亏
        mu0: 原假设均值（默认 0，即检验策略是否真的赚钱）
        alternative: "two-sided" / "greater" / "less"

    返回：
        dict 包含 ``t_stat``、``p_value``、``df``、``mean``、``std_err``、``significant_at_5pct``。

    说明：
        - 当 scipy 不可用时，p 值通过 t 分布 CDF 的数值积分（Lentz 算法 + 不完全 beta 函数）近似。
        - 样本数 < 2 时返回 NaN。
    """
    pnl = np.asarray(pnl_series, dtype=float)
    n = pnl.size

    if n < 2:
        return {
            "t_stat": float("nan"),
            "p_value": float("nan"),
            "df": max(n - 1, 0),
            "mean": float(pnl.mean()) if n > 0 else 0.0,
            "std_err": float("nan"),
            "alternative": alternative,
            "significant_at_5pct": False,
        }

    mean = float(pnl.mean())
    sd = float(pnl.std(ddof=1))
    if sd == 0.0:
        # 所有 PnL 完全相同：方差为 0，t 趋于 ±inf 或 0
        t_stat = float("inf") if mean > mu0 else (float("-inf") if mean < mu0 else 0.0)
        p_value = 0.0 if mean != mu0 else 1.0
        return {
            "t_stat": t_stat,
            "p_value": p_value,
            "df": n - 1,
            "mean": mean,
            "std_err": 0.0,
            "alternative": alternative,
            "significant_at_5pct": p_value < 0.05,
        }

    se = sd / math.sqrt(n)
    t_stat = (mean - mu0) / se
    df = n - 1

    if _HAS_SCIPY:
        if alternative == "two-sided":
            p_value = 2.0 * (1.0 - _scipy_stats.t.cdf(abs(t_stat), df=df))
        elif alternative == "greater":
            p_value = 1.0 - _scipy_stats.t.cdf(t_stat, df=df)
        elif alternative == "less":
            p_value = _scipy_stats.t.cdf(t_stat, df=df)
        else:
            raise ValueError(f"unknown alternative: {alternative!r}")
    else:
        cdf = _student_t_cdf(t_stat, df)
        if alternative == "two-sided":
            p_value = 2.0 * min(cdf, 1.0 - cdf)
        elif alternative == "greater":
            p_value = 1.0 - cdf
        elif alternative == "less":
            p_value = cdf
        else:
            raise ValueError(f"unknown alternative: {alternative!r}")

    return {
        "t_stat": float(t_stat),
        "p_value": float(p_value),
        "df": df,
        "mean": mean,
        "std_err": se,
        "alternative": alternative,
        "significant_at_5pct": float(p_value) < 0.05,
    }


# ---------------------------------------------------------------------------
# 2. 二项检验（胜率）
# ---------------------------------------------------------------------------


def binomial_test_win_rate(
    pnl_series: Sequence[float],
    p0: float = 0.5,
    alternative: str = "greater",
) -> dict:
    """
    二项精确检验：胜率是否显著高于 ``p0``。

    假设：
        H0: P(PnL > 0) = p0
        H1: P(PnL > 0) > p0   (alternative="greater")，类似有 "less" 和 "two-sided"

    每笔交易视为一次 Bernoulli(p) 试验，胜利次数 k ~ Binomial(n, p0) 在 H0 下。
    精确 p 值通过二项 PMF 求和得到（不做正态近似）。

    参数：
        pnl_series: 每笔交易盈亏
        p0: 原假设胜率（默认 0.5，即纯随机猜测的基线）
        alternative: "two-sided" / "greater" / "less"

    返回：
        dict 包含 ``wins``、``n_trades``、``observed_p``、``p_value``、
        ``significant_at_5pct``。
    """
    pnl = np.asarray(pnl_series, dtype=float)
    n = pnl.size
    if n == 0:
        return {
            "wins": 0,
            "n_trades": 0,
            "observed_p": 0.0,
            "p0": p0,
            "p_value": float("nan"),
            "alternative": alternative,
            "significant_at_5pct": False,
        }

    wins = int((pnl > 0).sum())
    observed_p = wins / n

    if _HAS_SCIPY:
        result = _scipy_stats.binomtest(wins, n=n, p=p0, alternative=alternative)
        p_value = float(result.pvalue)
    else:
        p_value = _binomial_p_value(wins, n, p0, alternative)

    return {
        "wins": wins,
        "n_trades": n,
        "observed_p": observed_p,
        "p0": p0,
        "p_value": p_value,
        "alternative": alternative,
        "significant_at_5pct": p_value < 0.05,
    }


# ---------------------------------------------------------------------------
# 3. Jarque-Bera 正态性检验
# ---------------------------------------------------------------------------


def jarque_bera_test(pnl_series: Sequence[float]) -> dict:
    """
    Jarque-Bera 正态性检验。

    统计量：
        JB = (n / 6) * (S^2 + (K - 3)^2 / 4)
    其中 S 是样本偏度（Skewness），K 是样本峰度（Kurtosis）。
    在正态假设下 JB 渐近服从自由度为 2 的卡方分布。

    用途：
        许多基于正态假设的指标（如普通 t 检验、参数法 VaR）在 PnL 严重偏斜
        或重尾时会失效。本检验帮助判断是否需要切换到 Bootstrap / 分位数法。

    返回：
        dict 包含 ``jb_stat``、``p_value``、``skewness``、``kurtosis``、
        ``excess_kurtosis``、``is_normal_at_5pct``（True 表示不拒绝正态原假设）。

    注意：JB 是渐近检验，n < 30 时检验势较弱，结果仅供参考。
    """
    pnl = np.asarray(pnl_series, dtype=float)
    n = pnl.size

    if n < 2:
        return {
            "jb_stat": float("nan"),
            "p_value": float("nan"),
            "skewness": float("nan"),
            "kurtosis": float("nan"),
            "excess_kurtosis": float("nan"),
            "n": n,
            "is_normal_at_5pct": False,
        }

    mean = pnl.mean()
    diff = pnl - mean
    m2 = float((diff ** 2).mean())
    m3 = float((diff ** 3).mean())
    m4 = float((diff ** 4).mean())

    if m2 == 0.0:
        return {
            "jb_stat": 0.0,
            "p_value": 1.0,
            "skewness": 0.0,
            "kurtosis": float("nan"),
            "excess_kurtosis": float("nan"),
            "n": n,
            "is_normal_at_5pct": True,
        }

    skewness = m3 / (m2 ** 1.5)
    kurtosis = m4 / (m2 ** 2)
    excess_kurtosis = kurtosis - 3.0
    jb = (n / 6.0) * (skewness ** 2 + (excess_kurtosis ** 2) / 4.0)

    if _HAS_SCIPY:
        p_value = float(1.0 - _scipy_stats.chi2.cdf(jb, df=2))
    else:
        # df=2 的卡方 CDF 有闭式解：F(x) = 1 - exp(-x/2)
        p_value = math.exp(-jb / 2.0)

    return {
        "jb_stat": float(jb),
        "p_value": p_value,
        "skewness": float(skewness),
        "kurtosis": float(kurtosis),
        "excess_kurtosis": float(excess_kurtosis),
        "n": n,
        "is_normal_at_5pct": p_value >= 0.05,
    }


# ---------------------------------------------------------------------------
# 内部数值实现（scipy 缺失时的回退）
# ---------------------------------------------------------------------------


def _student_t_cdf(t: float, df: int) -> float:
    """
    Student-t 分布 CDF 的数值实现。

    通过关系 F_t(x) = 1 - 0.5 * I_{df/(df+x^2)}(df/2, 1/2)（x > 0）
    其中 I_x(a, b) 是正则化不完全 beta 函数。

    这里直接利用 math.lgamma + 数值积分太复杂，使用 Lentz 连分式更稳定。
    为保持代码简洁，采用蒙特卡洛 + 精确级数混合的折中方案：
    用大样本数值积分（Simpson）近似 t 密度的累积概率，对回测场景足够精确。
    """
    if df < 1:
        return float("nan")
    if t == 0.0:
        return 0.5
    if math.isinf(t):
        return 1.0 if t > 0 else 0.0

    # 使用不完全 beta 函数关系
    # F_t(x) = 1 - 0.5 * I_z(df/2, 1/2)  其中 z = df / (df + x^2)，x > 0
    x = abs(t)
    z = df / (df + x * x)
    ibeta = _reg_incomplete_beta(z, df / 2.0, 0.5)
    cdf_pos = 1.0 - 0.5 * ibeta
    return cdf_pos if t > 0 else 1.0 - cdf_pos


def _reg_incomplete_beta(x: float, a: float, b: float) -> float:
    """
    正则化不完全 beta 函数 I_x(a, b)。

    使用 Numerical Recipes 中的 Lentz 连分式实现，适用于 0 < x < 1。
    """
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0

    # 前因子 bt = x^a * (1-x)^b / [a * B(a,b)]
    log_bt = (
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log(1.0 - x)
    )
    bt = math.exp(log_bt)

    # 选择更快收敛的级数方向
    if x < (a + 1.0) / (a + b + 2.0):
        cf = _betacf(x, a, b)
        return bt * cf / a
    else:
        cf = _betacf(1.0 - x, b, a)
        return 1.0 - bt * cf / b


def _betacf(x: float, a: float, b: float, max_iter: int = 200, eps: float = 3e-16) -> float:
    """Lentz 算法计算不完全 beta 函数的连分式部分。"""
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-300:
        d = 1e-300
    d = 1.0 / d
    h = d

    for m in range(1, max_iter + 1):
        m2 = 2 * m
        # 偶数步
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-300:
            d = 1e-300
        c = 1.0 + aa / c
        if abs(c) < 1e-300:
            c = 1e-300
        d = 1.0 / d
        h *= d * c
        # 奇数步
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-300:
            d = 1e-300
        c = 1.0 + aa / c
        if abs(c) < 1e-300:
            c = 1e-300
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            return h
    return h


def _binomial_p_value(k: int, n: int, p: float, alternative: str) -> float:
    """精确二项检验 p 值（直接对 PMF 求和，无正态近似）。"""
    if n == 0:
        return float("nan")

    log_pmf = [
        math.lgamma(n + 1)
        - math.lgamma(i + 1)
        - math.lgamma(n - i + 1)
        + i * math.log(p if p > 0 else 1e-300)
        + (n - i) * math.log(1.0 - p if p < 1 else 1e-300)
        for i in range(n + 1)
    ]
    pmf = [math.exp(lp) for lp in log_pmf]

    if alternative == "greater":
        return sum(pmf[k:])
    if alternative == "less":
        return sum(pmf[: k + 1])
    if alternative == "two-sided":
        # 双侧：把所有 PMF 不大于观测值 PMF 的点都算上（与 scipy 一致的"最小似然"法）
        observed = pmf[k]
        return sum(p_i for p_i in pmf if p_i <= observed + 1e-15)
    raise ValueError(f"unknown alternative: {alternative!r}")
