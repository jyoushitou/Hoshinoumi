# ===================== v18.19 自动备份 =====================

import os
import shutil
import sqlite3
import sys
import time
import types
import unittest


def _stub_missing_deps():
    def module(name, **attrs):
        m = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(m, k, v)
        sys.modules[name] = m
        return m

    try:
        import pymysql  # noqa: F401
    except ImportError:
        module("pymysql")
        module("pymysql.cursors", DictCursor=object)
        sys.modules["pymysql"].cursors = sys.modules["pymysql.cursors"]
        sys.modules["pymysql"].connect = lambda **kw: None
    for name, attrs in (("jieba", {"lcut": lambda s: list(s)}), ("PIL", {"Image": None})):
        try:
            __import__(name)
        except ImportError:
            module(name, **attrs)


_stub_missing_deps()

from bot.infra import backup  # noqa: E402


class TestBackup(unittest.TestCase):
    def setUp(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.root = os.path.join(base, ".tmp", f"backup-{os.getpid()}")
        shutil.rmtree(self.root, ignore_errors=True)
        os.makedirs(self.root, exist_ok=True)
        self.db = os.path.join(self.root, "src.db")
        c = sqlite3.connect(self.db)
        c.execute("CREATE TABLE a (id INTEGER PRIMARY KEY)")
        c.execute("INSERT INTO a DEFAULT VALUES")
        c.commit()
        c.close()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_sqlite_backup_and_index(self):
        r = backup.run_backup(sqlite_path=self.db, backend="sqlite", root=self.root)
        self.assertTrue(r["ok"], r)
        self.assertTrue(os.path.exists(os.path.join(self.root, r["file"])))
        self.assertGreater(r["tables"], 0)
        items = backup.list_backups(root=self.root)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["file"], r["file"])

    def test_prune_keeps_six(self):
        items = []
        for i in range(7):
            name = f"nao-2026-{i + 1:02d}.db"
            p = os.path.join(self.root, name)
            with open(p, "wb") as f:
                f.write(b"x")
            items.append({"file": name, "size": 1, "tables": 1, "ok": True,
                          "ts": time.time() - i * 1000})
        kept = backup._prune(self.root, items)
        self.assertEqual(len(kept), 6)
        self.assertEqual(len([f for f in os.listdir(self.root) if f.startswith("nao-")]), 6)

    def test_describe(self):
        backup.run_backup(sqlite_path=self.db, backend="sqlite", root=self.root)
        out = backup.describe(root=self.root)
        self.assertIn("备份", out)
        self.assertIn("表", out)


if __name__ == "__main__":
    unittest.main()
