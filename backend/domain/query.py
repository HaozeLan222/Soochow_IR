from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EngineQuery:
    """Engine 实际使用的查询模型。"""
    query: str
    field: str = "all"
    top_k: int = 10
    college: str | None = None
