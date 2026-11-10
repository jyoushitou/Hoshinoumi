# ===================== 事件定义（v17.1.0） =====================
# 统一的事件对象：不管来自哪里（聊天/定时/主动/空闲/通知），
# 调度器只认这一种东西。
#
#     Event(kind="schedule", key="c1", fn=..., priority=Priority.EVENT)
#
# 设计要点：
#   - kind + key 决定去重：同 kind 同 key 未完成时不重复入队
#   - priority 只有三档（P0 聊天 / P1 事件 / P2 空闲）
#   - timeout 到点取消；retries 只在非超时场景重试
#   - fn 是**无参** async 可调用（参数用闭包/functools.partial 绑好）

import time
import uuid
from dataclasses import dataclass, field
from enum import IntEnum


class Priority(IntEnum):
    """优先级：数字越小越优先"""

    CHAT = 0     # 聊天回复、命令：独占槽位，不排队
    EVENT = 1    # 定时任务、主动消息、系统通知
    IDLE = 2     # 读书、抓取、浓缩、日记


DEFAULT_TIMEOUT = 120.0


@dataclass
class Event:
    """一个待执行的事件"""

    kind: str                                  # schedule / proactive / idle_read / notice / chat
    key: str                                   # 去重键（同 kind 内唯一），如 "cron:c1"
    fn: object                                 # 无参 async 可调用
    priority: int = Priority.IDLE
    timeout: float = DEFAULT_TIMEOUT
    retries: int = 1                           # 失败重试次数（超时不重试）
    created_at: float = field(default_factory=time.time)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    def dedupe_key(self):
        """去重用的标识：kind:key"""
        return f"{self.kind}:{self.key}"

    def age(self, now=None):
        """入队多久了（秒）"""
        return max(0.0, (now or time.time()) - self.created_at)

    def __str__(self):
        return f"<Event {self.kind}:{self.key} p={int(self.priority)} id={self.id}>"
