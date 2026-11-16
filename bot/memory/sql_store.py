# ===================== SQLMemoryStore native（v31.1） =====================
# 包装现有 repo_memory；不另建表，不改变现有读写语义。

from ..infra import repo_memory
from ..ports.memory import MemoryItem


class SQLMemoryStore:
    name = "sql"

    async def add(self, user_id, item: MemoryItem):
        new_id = repo_memory.add_event_to_db(
            item.target_id, item.content,
            tags=item.keywords, kind=item.kind,
            importance=item.importance, due_date=item.due_date,
            user_id=user_id,
        )
        if new_id is None:
            raise ValueError("记忆为空或写入失败")
        return str(new_id)

    async def delete(self, user_id, item_id):
        from ..infra.conn import get_cursor
        c = get_cursor()
        try:
            c.execute("DELETE FROM memories WHERE id=%s AND user_id=%s",
                      (int(item_id), str(user_id)))
            c.connection.commit()
        finally:
            try:
                c.close()
            except Exception:
                pass

    async def recent(self, user_id, n):
        from ..infra.conn import get_cursor
        c = get_cursor()
        try:
            c.execute(
                "SELECT id, target_id, kind, summary, tags, importance, "
                "hit_count, created_at FROM memories WHERE user_id=%s "
                "ORDER BY id DESC LIMIT %s",
                (str(user_id), int(n)))
            return list(c.fetchall() or [])
        finally:
            try:
                c.close()
            except Exception:
                pass
