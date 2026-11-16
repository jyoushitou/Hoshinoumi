# ===================== 默认链路端口（v33.6） =====================

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class RouteKey:
    layer: str
    capability: str = ""
    user_id: str = "__owner__"
    scene: str = ""


@dataclass
class Candidate:
    origin: str
    name: str
    priority: int = 0
    health: str = "ok"


@runtime_checkable
class RouteRegistry(Protocol):
    def resolve(self, key: RouteKey) -> Candidate: ...
    def candidates(self, key: RouteKey) -> list: ...
