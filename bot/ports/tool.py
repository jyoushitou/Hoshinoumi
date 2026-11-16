# ===================== 工具端口（v33.2） =====================

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class ToolSpec:
    name: str
    description: str = ""
    schema: dict = field(default_factory=dict)
    permissions: tuple = ()


@runtime_checkable
class Tool(Protocol):
    name: str
    schema: dict
    permissions: set

    async def invoke(self, user_id: str, args: dict) -> dict: ...
