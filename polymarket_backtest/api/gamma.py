"""
Polymarket Gamma API 客户端

封装市场发现与合约信息查询，支持 BTC/ETH/SOL/XRP 的 15 分钟涨跌市场。

用法示例：
    from polymarket_backtest.api import GammaClient

    client = GammaClient()
    market = client.get_market_info("ETH")
    print(market.slug, market.up_price, market.down_price)

    # 列出近期市场
    markets = client.list_recent_markets("BTC", n=5)
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

import requests

from .models import MarketInfo


class GammaClient:
    """
    Polymarket Gamma API 客户端。

    用于发现市场和获取市场元数据（无需认证）。
    """

    BASE_URL = "https://gamma-api.polymarket.com"

    COIN_SLUGS: dict[str, str] = {
        "BTC": "btc-updown-15m",
        "ETH": "eth-updown-15m",
        "SOL": "sol-updown-15m",
        "XRP": "xrp-updown-15m",
    }
    SUPPORTED_COINS = list(COIN_SLUGS.keys())

    def __init__(self, base_url: str = BASE_URL, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def get_market_info(self, coin: str) -> MarketInfo | None:
        """
        获取某币种当前活跃的 15 分钟市场信息。

        参数：
            coin: 币种符号（BTC / ETH / SOL / XRP，不区分大小写）

        返回：
            MarketInfo 对象，无活跃市场时返回 None
        """
        market = self._get_active_market(coin.upper())
        if not market:
            return None
        return self._parse_market(market, coin.upper())

    def get_market_by_slug(self, slug: str) -> MarketInfo | None:
        """
        通过 slug 精确查询市场。

        参数：
            slug: 市场 slug，例如 "eth-updown-15m-1775035200"

        返回：
            MarketInfo 对象，未找到时返回 None
        """
        coin = self._coin_from_slug(slug)
        raw = self._fetch_by_slug(slug)
        if not raw:
            return None
        return self._parse_market(raw, coin)

    def list_recent_markets(self, coin: str, n: int = 10) -> list[MarketInfo]:
        """
        列出某币种最近 n 个市场（从当前窗口往前推算）。

        参数：
            coin: 币种符号
            n: 返回的市场数量

        返回：
            MarketInfo 列表（按时间从新到旧排列）
        """
        coin = coin.upper()
        self._check_coin(coin)
        prefix = self.COIN_SLUGS[coin]

        now = datetime.now(timezone.utc)
        minute = (now.minute // 15) * 15
        current_ts = int(now.replace(minute=minute, second=0, microsecond=0).timestamp())

        results: list[MarketInfo] = []
        ts = current_ts
        while len(results) < n:
            slug = f"{prefix}-{ts}"
            raw = self._fetch_by_slug(slug)
            if raw:
                results.append(self._parse_market(raw, coin))
            ts -= 900  # 往前 15 分钟
            if ts < current_ts - 900 * 200:  # 最多往前 200 个窗口（约 2 天）
                break

        return results

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _get_active_market(self, coin: str) -> dict[str, Any] | None:
        """尝试当前、下一个、上一个窗口，找到 acceptingOrders 的市场。"""
        self._check_coin(coin)
        prefix = self.COIN_SLUGS[coin]

        now = datetime.now(timezone.utc)
        minute = (now.minute // 15) * 15
        current_ts = int(now.replace(minute=minute, second=0, microsecond=0).timestamp())

        for offset in [0, 900, -900]:
            ts = current_ts + offset
            raw = self._fetch_by_slug(f"{prefix}-{ts}")
            if raw and raw.get("acceptingOrders"):
                return raw
        return None

    def _fetch_by_slug(self, slug: str, retries: int = 3) -> dict[str, Any] | None:
        """GET /markets/slug/{slug}，SSL 错误时自动重试。"""
        url = f"{self.base_url}/markets/slug/{slug}"
        for attempt in range(retries):
            try:
                resp = self._session.get(url, timeout=self.timeout)
                if resp.status_code == 200:
                    return resp.json()
                return None
            except Exception as e:
                err = str(e).lower()
                is_network = any(k in err for k in ("ssl", "eof", "tls", "connection"))
                if is_network and attempt < retries - 1:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                return None
        return None

    def _parse_market(self, raw: dict[str, Any], coin: str) -> MarketInfo:
        """将原始 API 响应解析为 MarketInfo。"""
        outcomes = self._parse_json_field(raw.get("outcomes", '["Up", "Down"]'))
        token_ids_raw = self._parse_json_field(raw.get("clobTokenIds", "[]"))
        prices_raw = self._parse_json_field(raw.get("outcomePrices", '["0.5", "0.5"]'))

        token_ids = {str(o).lower(): str(v) for o, v in zip(outcomes, token_ids_raw)}
        prices = {str(o).lower(): float(v) for o, v in zip(outcomes, prices_raw)}

        return MarketInfo(
            slug=raw.get("slug", ""),
            question=raw.get("question", ""),
            coin=coin,
            end_date=raw.get("endDate", ""),
            token_ids=token_ids,
            prices=prices,
            accepting_orders=bool(raw.get("acceptingOrders", False)),
            raw=raw,
        )

    @staticmethod
    def _parse_json_field(value: Any) -> list:
        if isinstance(value, str):
            return json.loads(value)
        return list(value)

    def _check_coin(self, coin: str) -> None:
        if coin not in self.COIN_SLUGS:
            raise ValueError(
                f"不支持的币种: {coin!r}。支持: {self.SUPPORTED_COINS}"
            )

    @staticmethod
    def _coin_from_slug(slug: str) -> str:
        slug_lower = slug.lower()
        for coin, prefix in GammaClient.COIN_SLUGS.items():
            if slug_lower.startswith(prefix):
                return coin
        return "UNKNOWN"
