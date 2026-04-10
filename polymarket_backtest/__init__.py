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
"""

__version__ = "0.1.0"
