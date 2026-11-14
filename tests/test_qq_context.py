# ===================== v23.5.1 QQ 入站 user_id 上下文 =====================
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path


def _stub():
    for name, attrs in (("jieba", {"lcut": lambda s: list(s)}), ("PIL", {"Image": None})):
        try:
            __import__(name)
        except ImportError:
            m = types.ModuleType(name)
            for k, v in attrs.items():
                setattr(m, k, v)
            sys.modules[name] = m


_stub()


class TestQqContext(unittest.TestCase):
    def setUp(self):
        from bot.infra import conn, schema, tenant
        self.tenant = tenant
        self.tmp = tempfile.mkdtemp()
        conn.configure(backend="sqlite", sqlite_path=str(Path(self.tmp) / "qq.db"))
        self.c = conn.get_cursor()
        schema.ensure_tables(self.c)
        from scripts import migrate_v23
        migrate_v23.apply(self.c)
        from bot.infra import cache
        cache.invalidate("cron:list")

    def tearDown(self):
        try:
            self.c.close()
        except Exception:
            pass
        from bot.infra import conn
        self.tenant.clear_user()
        conn.configure(backend=None, sqlite_path=None, mysql_config=None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_qq_user_auto_create(self):
        from bot.infra import repo_users
        a = repo_users.ensure_qq_user("10001")
        self.assertEqual(a["id"], "10001")
        self.assertEqual(a["role"], "user")
        self.assertEqual(repo_users.ensure_qq_user("10001")["id"], "10001")

    def test_context_isolates_memory_and_conversation(self):
        from bot.infra import repo_memory, repo_conversation
        self.tenant.use_user("10001")
        repo_memory.add_event_to_db("10001", "A 的事")
        repo_conversation.append(target_id="10001", content="A 的话")
        self.tenant.use_user("10002")
        repo_memory.add_event_to_db("10002", "B 的事")
        repo_conversation.append(target_id="10002", content="B 的话")

        self.tenant.use_user("10001")
        a = repo_memory.load_events_from_db("10001")
        self.tenant.use_user("10002")
        b = repo_memory.load_events_from_db("10002")
        self.assertTrue(any("A 的事" in x[0] for x in a))
        self.assertFalse(any("B 的事" in x[0] for x in a))
        self.assertTrue(any("B 的事" in x[0] for x in b))
        self.tenant.use_user("10001")
        ca = repo_conversation.recent("10001")
        self.tenant.use_user("10002")
        cb = repo_conversation.recent("10002")
        self.assertEqual([r["content"] for r in ca], ["A 的话"])
        self.assertEqual([r["content"] for r in cb], ["B 的话"])


if __name__ == "__main__":
    unittest.main()

