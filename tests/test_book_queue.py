# ===================== v24.7 本地阅读队列 =====================
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


class TestBookQueue(unittest.TestCase):
    def setUp(self):
        from bot.infra import conn, schema
        self.tmp = tempfile.mkdtemp()
        conn.configure(backend="sqlite", sqlite_path=str(Path(self.tmp) / "q.db"))
        self.c = conn.get_cursor()
        schema.ensure_tables(self.c)
        from bot.life import book_queue
        self.Q = book_queue

    def tearDown(self):
        try:
            self.c.close()
        except Exception:
            pass
        from bot.infra import conn
        conn.configure(backend=None, sqlite_path=None, mysql_config=None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_enqueue_front_and_done(self):
        self.Q.enqueue("u1", "A", 2)
        self.Q.enqueue("u1", "B", 3)
        self.assertEqual(self.Q.active("u1")["name"], "B")
        self.Q.set_progress("u1", "B", 3, 3)
        self.assertEqual(self.Q.active("u1")["name"], "A")
        self.Q.set_progress("u1", "A", 2, 2)
        self.assertIsNone(self.Q.active("u1"))
        self.assertEqual(len(self.Q.list_queue("u1")), 2)

    def test_user_isolated(self):
        self.Q.enqueue("u1", "A", 1)
        self.Q.enqueue("u2", "B", 1)
        self.assertEqual(self.Q.active("u1")["name"], "A")
        self.assertEqual(self.Q.active("u2")["name"], "B")

    def test_remove(self):
        self.Q.enqueue("u1", "A", 1)
        self.assertTrue(self.Q.remove("u1", "A"))
        self.assertIsNone(self.Q.active("u1"))


if __name__ == "__main__":
    unittest.main()
