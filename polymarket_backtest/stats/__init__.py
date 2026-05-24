"""
统计计算模块
============

将统计计算课程的核心方法应用于预测市场策略评估：

    - Bootstrap 重采样      —— 给任意回测指标（Sharpe、胜率等）配上置信区间
    - 假设检验              —— 用 t / 二项 / Jarque-Bera 检验回答"策略是否真的有效"
    - Monte Carlo 模拟      —— 基于经验分布生成未来权益曲线，估计 VaR / CVaR
    - Kelly 准则            —— 计算最大化长期对数财富的最优仓位

典型用法：

    from polymarket_backtest.data import load_trades
    from polymarket_backtest.stats import (
        bootstrap_sharpe_ci,
        ttest_mean_zero,
        monte_carlo_paths,
        monte_carlo_summary,
        kelly_fraction_from_pnl,
    )

    pnl = load_trades("flash_crash")["gross_pnl"].dropna().tolist()

    # 1. Sharpe 比率的 95% 置信区间
    print(bootstrap_sharpe_ci(pnl, n_bootstrap=2000, seed=42))

    # 2. 检验平均 PnL 是否显著大于零
    print(ttest_mean_zero(pnl, alternative="greater"))

    # 3. 模拟未来 100 期的 1000 条权益曲线
    paths = monte_carlo_paths(pnl, n_paths=1000, n_periods=100, seed=0)
    print(monte_carlo_summary(paths))

    # 4. Kelly 最优仓位
    print(kelly_fraction_from_pnl(pnl))
"""

from .bootstrap import (
    bootstrap_ci,
    bootstrap_mean_ci,
    bootstrap_sharpe_ci,
    bootstrap_win_rate_ci,
)
from .hypothesis import (
    binomial_test_win_rate,
    has_scipy,
    jarque_bera_test,
    ttest_mean_zero,
)
from .simulation import (
    kelly_fraction,
    kelly_fraction_from_pnl,
    monte_carlo_paths,
    monte_carlo_summary,
)

__all__ = [
    # bootstrap
    "bootstrap_ci",
    "bootstrap_sharpe_ci",
    "bootstrap_win_rate_ci",
    "bootstrap_mean_ci",
    # hypothesis
    "ttest_mean_zero",
    "binomial_test_win_rate",
    "jarque_bera_test",
    "has_scipy",
    # simulation
    "monte_carlo_paths",
    "monte_carlo_summary",
    "kelly_fraction",
    "kelly_fraction_from_pnl",
]
