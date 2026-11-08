# ===================== 时钟端口 =====================
# 目的：把 datetime.now() 收口，测试时能冻结时间

from datetime import datetime, timedelta, timezone
from typing import Protocol, runtime_checkable

CST = timezone(timedelta(hours=8))  # 东八区（与 config.CST 一致，但这里不依赖 config）


@runtime_checkable
class Clock(Protocol):
    """时间端口"""
    def now(self) -> datetime: ...


class SystemClock:
    """默认实现：东八区系统时钟"""

    def __init__(self, tz=timezone.utc):
        self._tz = tz

    def now(self) -> datetime:
        return datetime.now(self._tz)


def default_clock() -> Clock:
    """默认时钟（东八区）"""
    return SystemClock(CST)
