# ===================== 存储端口（v33.3） =====================

from typing import Protocol, runtime_checkable


@runtime_checkable
class StorageBackend(Protocol):
    name: str
    async def execute(self, sql: str, params: tuple = ()) -> list: ...
    async def transaction(self): ...


@runtime_checkable
class Repository(Protocol):
    async def get(self, user_id: str, key: str) -> dict | None: ...
    async def put(self, user_id: str, key: str, value: dict) -> None: ...
