# ===================== MySQL/SQLite native（v33.3.1） =====================

from ..infra.conn import get_cursor
from ..ports.storage import Repository, StorageBackend


class SQLStorage:
    name = "sql"

    async def execute(self, sql, params=()):
        c = get_cursor()
        try:
            c.execute(sql, params or None)
            if str(sql).lstrip().upper().startswith("SELECT"):
                return list(c.fetchall() or [])
            c.connection.commit()
            return []
        finally:
            try:
                c.close()
            except Exception:
                pass

    async def transaction(self):
        return _Txn()


class _Txn:
    def __enter__(self):
        self.c = get_cursor(); return self

    def __exit__(self, exc_type, exc, tb):
        try:
            self.c.connection.commit() if exc_type is None else self.c.connection.rollback()
        finally:
            try: self.c.close()
            except Exception: pass
        return False


class MetaRepository:
    """简单 KV 仓储，包 bot_meta；用于接口层示例。"""

    async def get(self, user_id, key):
        c = get_cursor()
        try:
            c.execute("SELECT v FROM bot_meta WHERE k=%s", (key,))
            row = c.fetchone()
            return {"value": row["v"]} if row else None
        finally:
            try: c.close()
            except Exception: pass

    async def put(self, user_id, key, value):
        import json
        c = get_cursor()
        try:
            c.execute("INSERT INTO bot_meta(k,v) VALUES(%s,%s) "
                      "ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                      (key, json.dumps(value, ensure_ascii=False)))
            c.connection.commit()
        finally:
            try: c.close()
            except Exception: pass


assert isinstance(SQLStorage(), StorageBackend)
