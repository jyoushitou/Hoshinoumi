# ===================== 前置建表测试（v17.5 起点） =====================

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


class FakeCursor:
    """记录执行的 SQL；SHOW TABLES 返回预设集合"""

    def __init__(self, tables=()):
        self.tables = set(tables)
        self.executed = []
        self.connection = types.SimpleNamespace(commit=lambda: None)

    def execute(self, sql, args=None):
        self.executed.append(" ".join(sql.split())[:60])
        if "SHOW TABLES" in sql.upper():
            self._rows = [{f"Tables_in_x": t} for t in self.tables]
        elif "CREATE TABLE" in sql.upper():
            name = sql.split("EXISTS", 1)[1].strip().split()[0].strip("(")
            self.tables.add(name)
            self._rows = []

    def fetchall(self):
        return getattr(self, "_rows", [])

    def close(self):
        pass


class TestSchema(unittest.TestCase):
    """表定义齐全、幂等建表、缺表检测"""

    def test_tables_defined(self):
        from bot.infra import schema

        for name in ("user_memory", "logs", "api_keys"):
            self.assertIn(name, schema.TABLES, f"缺现状表 {name}")
        self.assertNotIn("events", schema.VIEWS, "v19.5：events 兼容视图已删除")
        for name in ("targets", "relations", "memories", "settings"):
            self.assertIn(name, schema.TABLES, f"缺纯表 {name}")

    def test_required_present(self):
        from bot.infra import schema

        for name in schema.REQUIRED:
            self.assertIn(name, schema.TABLES)

    def test_missing_detects(self):
        from bot.infra import schema

        c = FakeCursor(tables=["logs"])
        miss = schema.missing_tables(c)
        self.assertIn("memories", miss)
        self.assertNotIn("logs", miss)

    def test_ensure_creates_only_missing(self):
        from bot.infra import schema

        c = FakeCursor(tables=["logs", "api_keys"])
        created = schema.ensure_tables(cursor=c)
        self.assertIn("memories", created)
        self.assertNotIn("logs", created, "已有的表不该重建")
        self.assertIn("targets", created, "新表也该建")

    def test_ensure_idempotent(self):
        from bot.infra import schema

        c = FakeCursor(tables=[])
        first = schema.ensure_tables(cursor=c)
        second = schema.ensure_tables(cursor=c)
        self.assertTrue(first)
        self.assertEqual(second, [], "第二次不该再建")

    def test_all_ddl_are_if_not_exists(self):
        from bot.infra import schema

        for name, ddl in schema.TABLES.items():
            self.assertIn("IF NOT EXISTS", ddl.upper(), f"{name} 的 DDL 不是幂等的")

    def test_describe(self):
        from bot.infra import schema

        c = FakeCursor(tables=list(schema.TABLES))
        self.assertIn("齐全", schema.describe(c))


if __name__ == "__main__":
    unittest.main()
