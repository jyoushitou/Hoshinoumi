# ===================== 后端互导测试（v17.11 U4） =====================

import os
import shutil
import sqlite3
import sys
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

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import migrate_backend as M  # noqa: E402


class TestMigrateBackend(unittest.TestCase):
    """搬表的三个动作：读 / 写（幂等）/ 校验行数"""

    def setUp(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.dir = os.path.join(root, ".tmp", f"migrate-{os.getpid()}")
        shutil.rmtree(self.dir, ignore_errors=True)
        os.makedirs(self.dir, exist_ok=True)

        self.src = sqlite3.connect(os.path.join(self.dir, "src.db"))
        self.src.row_factory = sqlite3.Row
        self.dst = sqlite3.connect(os.path.join(self.dir, "dst.db"))
        self.dst.row_factory = sqlite3.Row

        self.src.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT)")
        self.src.executemany("INSERT INTO t(id,name) VALUES(?,?)",
                             [(1, "甲"), (2, "乙"), (3, "丙")])
        self.src.commit()
        self.dst.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT)")
        self.dst.commit()

    def tearDown(self):
        self.src.close()
        self.dst.close()
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_list_tables(self):
        self.assertIn("t", M.list_tables(self.src, "sqlite"))

    def test_columns_and_count(self):
        self.assertEqual(M.columns(self.src, "sqlite", "t"), ["id", "name"])
        self.assertEqual(M.count(self.src, "sqlite", "t"), 3)

    def test_read_rows(self):
        rows = M.read_rows(self.src, "sqlite", "t", ["id", "name"])
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["name"], "甲")

    def test_write_is_idempotent(self):
        rows = M.read_rows(self.src, "sqlite", "t", ["id", "name"])
        self.assertEqual(M.write_rows(self.dst, "sqlite", "t", ["id", "name"], rows), 3)
        M.write_rows(self.dst, "sqlite", "t", ["id", "name"], rows)   # 再写一次
        self.assertEqual(M.count(self.dst, "sqlite", "t"), 3, "重复写不该翻倍")

    def test_migrate_table_dry_run(self):
        src_n, moved, dst_n, err = M.migrate_table(self.src, "sqlite", self.dst,
                                                   "sqlite", "t", dry=True)
        self.assertIsNone(err)
        self.assertEqual(src_n, 3)
        self.assertEqual(moved, 0, "dry-run 不搬")
        self.assertEqual(M.count(self.dst, "sqlite", "t"), 0)

    def test_migrate_table_apply(self):
        src_n, moved, dst_n, err = M.migrate_table(self.src, "sqlite", self.dst,
                                                   "sqlite", "t", dry=False)
        self.assertIsNone(err)
        self.assertEqual(src_n, 3)
        self.assertEqual(moved, 3)
        self.assertEqual(dst_n, 3)

    def test_column_mismatch_reported(self):
        self.dst.execute("CREATE TABLE other (x INTEGER)")
        src_n, moved, dst_n, err = M.migrate_table(self.src, "sqlite", self.dst,
                                                   "sqlite", "other", dry=False)
        self.assertIsNotNone(err, "没有同名列要报错而不是静默")


if __name__ == "__main__":
    unittest.main()
