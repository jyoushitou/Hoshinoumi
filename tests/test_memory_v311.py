# ===================== v31.1 SQLMemoryStore =====================
import asyncio
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path

try:
    import jieba  # noqa: F401
except ImportError:
    m = types.ModuleType("jieba")
    m.lcut = lambda s: list(s)
    sys.modules["jieba"] = m

from bot.memory.sql_store import SQLMemoryStore
from bot.ports.memory import MemoryItem, MemoryStore


class TestSQLMemoryStore(unittest.TestCase):
    def setUp(self):
        from bot.infra import conn, schema
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        conn.configure(backend="sqlite", sqlite_path=str(Path(self.tmp) / "m.db"))
        self.c = conn.get_cursor()
        schema.ensure_tables(self.c, names=["memories"])
        try:
            self.c.execute("ALTER TABLE memories ADD COLUMN user_id VARCHAR(64) DEFAULT '__owner__'")
        except Exception:
            pass
        self.c.connection.commit()
        self.store = SQLMemoryStore()

    def tearDown(self):
        try:
            self.c.close()
        except Exception:
            pass
        from bot.infra import conn
        conn.configure(backend=None, sqlite_path=None, mysql_config=None)

    def test_add_recent_delete_scoped(self):
        async def run():
            i1 = await self.store.add("u1", MemoryItem("t1", "event", "A 的秘密"))
            await self.store.add("u2", MemoryItem("t2", "event", "B 的秘密"))
            self.assertIsInstance(self.store, MemoryStore)
            self.assertTrue(await self.store.recent("u1", 10))
            await self.store.delete("u2", i1)  # 不能删 u1
            self.assertTrue(await self.store.recent("u1", 10))
            await self.store.delete("u1", i1)
            self.assertEqual(await self.store.recent("u1", 10), [])
        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
