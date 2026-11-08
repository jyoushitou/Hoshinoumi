# ===================== 记忆端口 =====================
# 存一条记忆、查一批记忆、把文本变成向量

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal, Optional, Protocol, runtime_checkable


@dataclass
class MemoryItem:
    """一条记忆（对应 events 表的一行）"""
    target_id: str
    kind: Literal["event", "fact", "preference", "promise", "life", "profile", "summary"]
    content: str
    keywords: str = ""
    importance: int = 3
    due_date: Optional[date] = None
    hit_count: int = 0
    created_at: Optional[datetime] = None


@dataclass
class Query:
    """一次检索请求"""
    target_id: str
    text: str
    kinds: list = field(default_factory=list)   # 限定类别，空表示全部
    top_k: int = 5


@runtime_checkable
class MemoryStore(Protocol):
    """记忆存储端口"""

    async def add(self, item: MemoryItem) -> None: ...
    async def search(self, q: Query) -> list: ...
    async def recent(self, target_id: str, n: int) -> list: ...


@runtime_checkable
class Embedder(Protocol):
    """文本向量化端口（本地 bge 或远程都可以实现）"""

    dim: int

    def embed(self, texts: list) -> "object":
        """返回 (n, dim) 的矩阵；具体类型由实现决定（numpy 数组即可）"""
        ...


@runtime_checkable
class Retriever(Protocol):
    """检索端口：关键词 / 向量 / 混合，都实现它"""

    async def retrieve(self, q: Query) -> list: ...
