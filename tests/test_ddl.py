# ===================== DDL 方言适配测试（v17.11 U3） =====================

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


class TestAdaptDdl(unittest.TestCase):
    """MySQL DDL → SQLite"""

    def _one(self, ddl):
        from botv.infra.schema import adapt_ddl

        return adapt_ddl(ddl, "sqlite")[0]

    def test_autoincrement(self):
        out = self._one("CREATE TABLE t (id BIGINT AUTO_INCREMENT PRIMARY KEY)")
        self.assertIn("INTEGER PRIMARY KEY AUTOINCREMENT", out)
        self.assertNotIn("AUTO_INCREMENT", out)

    def test_bigint_becomes_integer(self):
        out = self._one("CREATE TABLE t (n BIGINT NULL)")
        self.assertIn("INTEGER", out)
        self.assertNotIn("BIGINT", out)

    def test_enum_becomes_text(self):
        out = self._one("CREATE TABLE t (k ENUM('a','b') NOT NULL)")
        self.assertIn("TEXT", out)
        self.assertNotIn("ENUM", out)

    def test_tinyint_bool(self):
        out = self._one("CREATE TABLE t (on_off TINYINT(1) NOT NULL DEFAULT 1)")
        self.assertIn("INTEGER", out)
        self.assertNotIn("TINYINT", out)

    def test_table_options_stripped(self):
        out = self._one("CREATE TABLE t (id INT) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")
        self.assertNotIn("ENGINE", out)
        self.assertNotIn("CHARSET", out)

    def test_on_update_stripped(self):
        out = self._one("CREATE TABLE t (u DATETIME DEFAULT CURRENT_TIMESTAMP "
                        "ON UPDATE CURRENT_TIMESTAMP)")
        self.assertNotIn("ON UPDATE", out)
        self.assertIn("CURRENT_TIMESTAMP", out)

    def test_comment_stripped(self):
        out = self._one("CREATE TABLE t (c INT COMMENT '说明')")
        self.assertNotIn("COMMENT", out)

    def test_key_becomes_index(self):
        from botv.infra.schema import adapt_ddl

        stmts = adapt_ddl(
            "CREATE TABLE t (a INT, b INT, KEY idx_a (a), "
            "UNIQUE KEY uk_ab (a, b)) ENGINE=InnoDB", "sqlite")
        self.assertEqual(len(stmts), 3, "建表 + 两个索引")
        self.assertIn("CREATE INDEX IF NOT EXISTS idx_a ON t(a)", stmts)
        self.assertIn("CREATE UNIQUE INDEX IF NOT EXISTS uk_ab ON t(a,b)", stmts)
        self.assertNotIn("KEY idx_a", stmts[0])

    def test_mysql_passthrough(self):
        from botv.infra.schema import adapt_ddl

        ddl = "CREATE TABLE t (id BIGINT AUTO_INCREMENT PRIMARY KEY) ENGINE=InnoDB"
        self.assertEqual(adapt_ddl(ddl, "mysql"), [ddl], "mysql 原样返回")

    def test_all_real_tables_parse(self):
        """仓库里 22 张表都能翻译，且不残留 MySQL 关键字"""
        from botv.infra import schema

        for name, ddl in schema.TABLES.items():
            stmts = schema.adapt_ddl(ddl, "sqlite")
            head = stmts[0]
            for bad in ("AUTO_INCREMENT", "ENGINE=", "ENUM(", "ON UPDATE", "UNSIGNED"):
                self.assertNotIn(bad, head, f"{name} 还残留 {bad}")
            self.assertTrue(head.strip().startswith("CREATE TABLE"), name)


class TestSqliteSchema(unittest.TestCase):
    """真的在 SQLite 里建全部表"""

    def test_create_all_and_idempotent(self):
        import os
        import shutil

        from botv.core import settings

        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        d = os.path.join(root, ".tmp", f"schema-{os.getpid()}")
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d, exist_ok=True)

        old_env = (os.environ.get("NAO_DB_BACKEND"), os.environ.get("NAO_DB_PATH"))
        os.environ["NAO_DB_BACKEND"] = "sqlite"
        os.environ["NAO_DB_PATH"] = os.path.join(d, "nao.db")
        settings._cache = None
        settings._backend_cache["value"] = None

        from botv.infra import conn, schema

        conn._local.__dict__.clear()
        try:
            created = schema.ensure_tables()
            self.assertEqual(len(created), len(schema.TABLES), "应建出全部表")
            self.assertEqual(schema.ensure_tables(), [], "再跑一次不该建任何表")
            self.assertEqual(schema.missing_tables(conn.get_cursor()), [])
        finally:
            conn._local.__dict__.clear()
            for k, v in zip(("NAO_DB_BACKEND", "NAO_DB_PATH"), old_env):
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
            settings._cache = None
            settings._backend_cache["value"] = None
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
