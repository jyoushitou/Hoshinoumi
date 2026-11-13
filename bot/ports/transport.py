# ===================== 传输端口 =====================
# 往哪儿发（私聊/群）、发什么（文本/图片/语音）、怎么发

from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable


@dataclass
class Target:
    """投递目标"""
    kind: Literal["private", "group"]
    id: int | str      # 私聊是 QQ 号，群聊是群号


@dataclass
class Segment:
    """一个消息段（对应 NapCat 的一段 message）"""
    type: Literal["text", "image", "face", "record", "at", "reply"]
    data: dict = field(default_factory=dict)


@runtime_checkable
class Transport(Protocol):
    """传输端口：QQ WebSocket 是它的一个实现，未来可以是别的平台"""

    async def send(self, target: Target, segments: list[Segment]) -> None:
        """发送一条消息（多个段合成一条）"""
        ...

    async def poke(self, target: Target, user_id: int | str) -> None:
        """戳一戳"""
        ...
