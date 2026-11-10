# ===================== 事件注册表（v17.1.0） =====================
# kind → 处理函数。调度器拿到 Event 后，用它查「这一类事件由谁来处理」。
#
#     @register("idle_read", priority=Priority.IDLE, timeout=180)
#     async def handle_idle_read(ev):
#         ...
#
# 设计要点：
#   - 注册是**显式**的：没注册的 kind 直接报错，不静默丢弃
#   - 同一个 kind 重复注册 → 报错（早发现拼错）
#   - 注册时可以带默认的 priority/timeout，Event 里没写就用默认
#   - handler 接收 Event，返回任意值（调度器只记录，不关心内容）

from dataclasses import dataclass, field

from .base import DEFAULT_TIMEOUT, Priority


@dataclass
class Handler:
    """一个 kind 的处理器与默认参数"""

    kind: str
    fn: object                                  # async def fn(ev)
    priority: int = Priority.IDLE
    timeout: float = DEFAULT_TIMEOUT
    description: str = ""
    retries: int = 1                            # 默认重试次数
    calls: int = field(default=0)               # 调用次数（观测用）
    failures: int = field(default=0)


_handlers = {}


def register(kind, priority=None, timeout=None, description="", retries=1):
    """注册装饰器：把 async 函数绑到某个 kind"""

    def deco(fn):
        if kind in _handlers:
            raise ValueError(f"kind 重复注册：{kind}")
        if not callable(fn):
            raise TypeError(f"{kind} 的处理器不可调用")
        _handlers[kind] = Handler(
            kind=kind,
            fn=fn,
            priority=Priority.IDLE if priority is None else priority,
            timeout=DEFAULT_TIMEOUT if timeout is None else timeout,
            description=description,
            retries=max(1, int(retries)),
        )
        return fn

    return deco


def get(kind):
    """取处理器；没注册返回 None"""
    return _handlers.get(kind)


def require(kind):
    """取处理器；没注册抛错（调度器入队时用）"""
    h = _handlers.get(kind)
    if h is None:
        raise KeyError(f"未注册的事件类型：{kind}")
    return h


def kinds():
    """已注册的所有 kind"""
    return sorted(_handlers)


def snapshot():
    """观测用：[{kind, priority, calls, failures}]"""
    return [
        {
            "kind": h.kind,
            "priority": int(h.priority),
            "calls": h.calls,
            "failures": h.failures,
            "description": h.description,
        }
        for h in sorted(_handlers.values(), key=lambda x: (int(x.priority), x.kind))
    ]


def clear():
    """测试用：清空注册表"""
    _handlers.clear()
