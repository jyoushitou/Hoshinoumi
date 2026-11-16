# ===================== 通道端口（v33.1） =====================
# 入站消息 / 出站通道；QQ/NapCat 是 native，第三方通道走插件。

from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable


@dataclass
class InboundMessage:
    source: str
    user_id: str
    target: str
    text: str
    is_group: bool = False
    raw: dict = field(default_factory=dict)


@runtime_checkable
class Channel(Protocol):
    name: str

    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def send(self, target: str, text: str, is_group: bool = False) -> bool: ...
    def on_message(self, handler) -> None: ...
