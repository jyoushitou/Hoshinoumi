# ===================== 调度端口（v33.4） =====================

from typing import Protocol, runtime_checkable


@runtime_checkable
class Trigger(Protocol):
    name: str
    async def next_at(self, now): ...


@runtime_checkable
class Scheduler(Protocol):
    name: str
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def schedule(self, trigger: Trigger, callback) -> str: ...
    async def cancel(self, task_id: str) -> None: ...
