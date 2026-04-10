"""
Polymarket API 数据模型

定义 API 调用的输入输出数据结构。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MarketInfo:
    """Polymarket 市场信息。"""

    slug: str
    question: str
    coin: str
    end_date: str
    token_ids: dict[str, str]    # {"up": "token_id", "down": "token_id"}
    prices: dict[str, float]     # {"up": 0.52, "down": 0.48}
    accepting_orders: bool
    raw: dict = field(default_factory=dict, repr=False)

    @property
    def up_token_id(self) -> str | None:
        return self.token_ids.get("up")

    @property
    def down_token_id(self) -> str | None:
        return self.token_ids.get("down")

    @property
    def up_price(self) -> float:
        return self.prices.get("up", 0.5)

    @property
    def down_price(self) -> float:
        return self.prices.get("down", 0.5)


@dataclass
class PricePoint:
    """单个历史价格点。"""

    timestamp: int    # Unix UTC
    price: float

    def __repr__(self) -> str:
        return f"PricePoint(t={self.timestamp}, p={self.price:.4f})"


@dataclass
class OddsHistory:
    """某 token 的赔率历史时间序列。"""

    token_id: str
    interval: str
    fidelity: int                # 分辨率（分钟）
    points: list[PricePoint] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.points)

    def prices(self) -> list[float]:
        return [p.price for p in self.points]

    def timestamps(self) -> list[int]:
        return [p.timestamp for p in self.points]
