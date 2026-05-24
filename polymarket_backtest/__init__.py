"""
polymarket-backtest
===================

Polymarket API 封装与策略回测评估工具包。

快速开始：
    # 1. 查询市场信息
    from polymarket_backtest.api import GammaClient, ClobClient

    gamma = GammaClient()
    market = gamma.get_market_info("BTC")
    print(market.slug, market.up_price)

    # 2. 拉取赔率历史
    clob = ClobClient()
    history = clob.get_price_history(market.up_token_id, interval="1d")
    print(f"{len(history)} 个价格点")

    # 3. 加载内置示例数据集
    from polymarket_backtest.data import load_trades, load_orderbook

    trades = load_trades("flash_crash")
    ob = load_orderbook("BTC")

    # 4. 计算回测指标
    from polymarket_backtest.backtest import summary

    pnl = trades["gross_pnl"].dropna().tolist()
    result = summary(pnl)
    print(result)
    # {'net_pnl': 47.92, 'win_rate': 0.143, 'sharpe_ratio': 0.85, 'max_drawdown': 12.5, ...}

    # 5. 统计推断（Bootstrap / 假设检验 / Monte Carlo / Kelly）
    from polymarket_backtest.stats import (
        bootstrap_sharpe_ci,
        ttest_mean_zero,
        monte_carlo_paths,
        monte_carlo_summary,
        kelly_fraction_from_pnl,
    )

    ci = bootstrap_sharpe_ci(pnl, n_bootstrap=2000, seed=42)
    print(ci)        # Sharpe 比率的 95% 置信区间
    print(ttest_mean_zero(pnl, alternative="greater"))
    paths = monte_carlo_paths(pnl, n_paths=1000, n_periods=100, seed=0)
    print(monte_carlo_summary(paths))
    print(kelly_fraction_from_pnl(pnl))
"""

from . import stats  # noqa: F401  顶层导出，便于 `import polymarket_backtest as pmb; pmb.stats`

__version__ = "0.1.0"
