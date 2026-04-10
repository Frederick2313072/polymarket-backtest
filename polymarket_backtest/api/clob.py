"""
Polymarket CLOB API 客户端（只读）

封装赔率历史数据查询。无需认证。

用法示例：
    from polymarket_backtest.api import GammaClient, ClobClient

    gamma = GammaClient()
    clob  = ClobClient()

    market = gamma.get_market_info("BTC")
    history = clob.get_price_history(market.up_token_id, interval="1d")

    for point in history.points:
        print(point.timestamp, point.price)
"""

from __future__ import annotations

from typing import Literal

import requests

from .models import OddsHistory, PricePoint

Interval = Literal["1m", "1h", "6h", "1d", "1w", "max"]


class ClobClient:
    """
    Polymarket CLOB API 客户端（只读子集）。

    提供赔率历史查询，无需 API 密钥。
    """

    BASE_URL = "https://clob.polymarket.com"

    def __init__(self, base_url: str = BASE_URL, timeout: int = 15):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def get_price_history(
        self,
        token_id: str,
        interval: Interval | None = "1d",
        fidelity: int = 60,
        start_ts: int | None = None,
        end_ts: int | None = None,
    ) -> OddsHistory:
        """
        拉取某 token 的赔率历史时间序列。

        参数：
            token_id: CLOB token ID（从 GammaClient 获取）
            interval: 时间窗口（"1m","1h","6h","1d","1w","max"）
                      与 start_ts/end_ts 互斥
            fidelity: 数据分辨率（分钟），例如 60 = 每小时一个点
            start_ts: 开始时间 Unix 时间戳（UTC）
            end_ts:   结束时间 Unix 时间戳（UTC）

        返回：
            OddsHistory 对象，包含时间戳和对应价格列表

        示例：
            # 拉取最近 1 天数据，每小时一个点
            history = clob.get_price_history(token_id, interval="1d", fidelity=60)

            # 拉取指定时间范围
            history = clob.get_price_history(
                token_id,
                start_ts=1697875200,
                end_ts=1697961600,
                fidelity=5,
            )
        """
        params: dict = {"market": token_id, "fidelity": fidelity}

        if start_ts is not None or end_ts is not None:
            if start_ts is not None:
                params["startTs"] = start_ts
            if end_ts is not None:
                params["endTs"] = end_ts
        elif interval is not None:
            params["interval"] = interval

        url = f"{self.base_url}/prices-history"
        resp = self._session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()

        data = resp.json()
        raw_points = data.get("history", [])
        points = [PricePoint(timestamp=int(p["t"]), price=float(p["p"])) for p in raw_points]

        return OddsHistory(
            token_id=token_id,
            interval=interval or "custom",
            fidelity=fidelity,
            points=points,
        )

    def get_price_history_df(
        self,
        token_id: str,
        interval: Interval | None = "1d",
        fidelity: int = 60,
        start_ts: int | None = None,
        end_ts: int | None = None,
    ):
        """
        同 get_price_history，但直接返回 pandas DataFrame。

        DataFrame 列：timestamp（Unix）、price、datetime（UTC）
        """
        import pandas as pd

        history = self.get_price_history(
            token_id,
            interval=interval,
            fidelity=fidelity,
            start_ts=start_ts,
            end_ts=end_ts,
        )
        if not history.points:
            return pd.DataFrame(columns=["timestamp", "price", "datetime"])

        df = pd.DataFrame(
            {"timestamp": history.timestamps(), "price": history.prices()}
        )
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
        return df
