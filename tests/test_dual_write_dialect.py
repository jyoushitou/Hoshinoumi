# ===================== v27.4 SQLite 双写方言 =====================
import sys
import types
import unittest
from unittest import mock

try:
    import jieba  # noqa: F401
except ImportError:
    m = types.ModuleType("jieba")
    m.lcut = lambda s: list(s)
    sys.modules["jieba"] = m


class _Cur:
    def __init__(self):
        self.sql = []
        self.connection = self

    def execute(self, sql, params=None):
        self.sql.append((sql, params))

    def commit(self):
        pass


class TestDualWriteDialect(unittest.TestCase):
    def test_sqlite_uses_insert_or_replace(self):
        from bot.infra import repo_memory

        cur = _Cur()
        with mock.patch("bot.infra.conn._resolve_backend", return_value="sqlite"), \
             mock.patch("bot.infra.repo_memory.get_cursor", return_value=cur):
            ok = repo_memory.dual_write("state", "1", '{"mood": 0.2}', user_id="u1")
        self.assertTrue(ok)
        sql = cur.sql[0][0]
        self.assertIn("INSERT OR REPLACE INTO bot_states", sql)
        self.assertNotIn("ON DUPLICATE KEY", sql)

    def test_mysql_uses_on_duplicate(self):
        from bot.infra import repo_memory

        cur = _Cur()
        with mock.patch("bot.infra.conn._resolve_backend", return_value="mysql"), \
             mock.patch("bot.infra.repo_memory.get_cursor", return_value=cur):
            ok = repo_memory.dual_write("state", "1", '{"mood": 0.2}', user_id="u1")
        self.assertTrue(ok)
        sql = cur.sql[0][0]
        self.assertIn("ON DUPLICATE KEY UPDATE", sql)


if __name__ == "__main__":
    unittest.main()
