# ===================== 命令注册表 =====================
# 用装饰器注册命令，替代原来的 if/elif 长链
# 约定：handler 接收 CommandContext，返回要发送的文本（空字符串表示不发）

from dataclasses import dataclass, field
from typing import Awaitable, Callable, Optional


@dataclass
class CommandContext:
    """一次命令调用的上下文"""
    parts: list          # 完整分词，含命令名本身（与旧代码保持一致）
    uid: str             # 发送者 QQ
    ws: object           # 当前 WebSocket 连接
    is_group: bool       # 是否群聊
    gid: int             # 群号（私聊为 0）

    @property
    def args(self) -> list:
        """去掉命令名后的参数列表"""
        return self.parts[1:]


@dataclass
class Command:
    """一个命令的元数据与处理器"""
    name: str
    handler: Callable[[CommandContext], Awaitable[str]]
    help_text: str = ""


COMMANDS: dict = {}  # {命令名: Command}


def command(name, help_text=""):
    """装饰器：把函数注册成命令"""
    def deco(fn):
        COMMANDS[name] = Command(name=name, handler=fn, help_text=help_text)
        return fn
    return deco


def has(name) -> bool:
    """命令是否已迁移到注册表"""
    return name in COMMANDS


async def run(name, ctx) -> str:
    """执行命令，返回要发送的文本"""
    return await COMMANDS[name].handler(ctx)
