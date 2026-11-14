# ===================== v23.2 双用户隔离 =====================
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path


def _stub_missing_deps():
    for name, attrs in (("jieba", {"lcut": lambda s: list(s)}),
                        ("PIL", {"Image": None})):
        try:
            __import__(name)
        except ImportError:
            m = types.ModuleType(name)
            for k, v in attrs.items():
                setattr(m, k, v)
            sys.modules[name] = m


_stub_missing_deps()


class TestTenantIsolation(unittest.TestCase):
    def setUp(self):
        from bot.infra import conn, schema
        from scripts import migrate_v23
        self.tmp = tempfile.mkdtemp()
        self.path = str(Path(self.tmp) / "tenant.db")
        conn.configure(backend="sqlite", sqlite_path=self.path)
        self.c = conn.get_cursor()
        schema.ensure_tables(self.c)
        migrate_v23.apply(self.c)

        from bot.infra import repo_conversation, repo_memory
        from bot.schedule import cron
        # A
        repo_memory.add_event_to_db("u_a", "A 的秘密", user_id="u_a")
        cron.add("u_a", "daily", "A 的提醒", at_time="07:00", user_id="u_a")
        repo_conversation.append(user_id="u_a", target_id="u_a",
                                 content="A 的消息", message_id="a1")
        self.c.execute("INSERT INTO diaries(user_id,target_id,diary_date,content) "
                       "VALUES(%s,%s,%s,%s)", ("u_a", "u_a", "2026-11-14", "A 的日记"))
        # B
        repo_memory.add_event_to_db("u_b", "B 的秘密", user_id="u_b")
        cron.add("u_b", "daily", "B 的提醒", at_time="08:00", user_id="u_b")
        repo_conversation.append(user_id="u_b", target_id="u_b",
                                 content="B 的消息", message_id="b1")
        self.c.execute("INSERT INTO diaries(user_id,target_id,diary_date,content) "
                       "VALUES(%s,%s,%s,%s)", ("u_b", "u_b", "2026-11-14", "B 的日记"))
        self.c.connection.commit()

    def tearDown(self):
        try:
            self.c.close()
        except Exception:
            pass
        from bot.infra import conn
        conn.configure(backend=None, sqlite_path=None, mysql_config=None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_memory_isolation(self):
        from bot.infra import repo_tenant
        a = repo_tenant.memory_events("u_a", "u_a")
        b = repo_tenant.memory_events("u_b", "u_b")
        self.assertTrue(any("A 的秘密" in x[0] for x in a))
        self.assertFalse(any("B 的秘密" in x[0] for x in a))
        self.assertTrue(any("B 的秘密" in x[0] for x in b))
        self.assertFalse(any("A 的秘密" in x[0] for x in b))

    def test_conversation_isolation(self):
        from bot.infra import repo_tenant
        a = repo_tenant.conversation_recent("u_a", "u_a")
        b = repo_tenant.conversation_recent("u_b", "u_b")
        self.assertEqual([r["content"] for r in a], ["A 的消息"])
        self.assertEqual([r["content"] for r in b], ["B 的消息"])

    def test_cron_isolation(self):
        from bot.infra import repo_tenant
        a = repo_tenant.cron_list("u_a")
        b = repo_tenant.cron_list("u_b")
        self.assertEqual([r["content"] for r in a], ["A 的提醒"])
        self.assertEqual([r["content"] for r in b], ["B 的提醒"])

    def test_diary_isolation(self):
        from bot.infra import repo_tenant
        self.assertEqual(repo_tenant.diary_get("u_a", "2026-11-14", "u_a"), "A 的日记")
        self.assertEqual(repo_tenant.diary_get("u_b", "2026-11-14", "u_b"), "B 的日记")
        self.assertIsNone(repo_tenant.diary_get("u_a", "2026-11-14", "u_b"))

    def test_missing_user_rejected(self):
        from bot.infra import repo_tenant, tenant
        with self.assertRaises(tenant.TenantError):
            repo_tenant.cron_list("")


if __name__ == "__main__":
    unittest.main()
