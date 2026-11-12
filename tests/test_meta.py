# ===================== 元数据与 uptime 测试（v18.5） =====================

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


class TestRepoMeta(unittest.TestCase):
    """v18.5：启动时间存 bot_meta，不靠 logs 表"""

    def setUp(self):
        from botv.infra import schema

        schema.ensure_tables()   # 确保 bot_meta 存在

    def test_mark_start_idempotent(self):
        from botv.infra import repo_meta

        first = repo_meta.mark_start("18.5.0")
        again = repo_meta.mark_start("18.5.1")
        self.assertTrue(first)
        self.assertEqual(first, again, "首次启动时间不该被覆盖")

    def test_uptime_text(self):
        from botv.infra import repo_meta

        got = repo_meta.uptime_text()
        self.assertIsNotNone(got)
        text, start = got
        self.assertIn("天", text)
        self.assertIsNotNone(start.year)

    def test_get_missing_returns_default(self):
        from botv.infra import repo_meta

        self.assertEqual(repo_meta.get_value("不存在的键", "默认"), "默认")


class TestViews(unittest.TestCase):
    """v18.5：视图方言适配"""

    def test_sqlite_adapt(self):
        from botv.infra import schema

        ddl = schema.VIEWS["v_bot_meta"]
        # 强制按 sqlite 翻译
        import botv.infra.conn as conn

        orig = conn._resolve_backend
        conn._resolve_backend = lambda: "sqlite"
        try:
            out = schema._adapt_view(ddl)
        finally:
            conn._resolve_backend = orig
        self.assertIn("CREATE VIEW IF NOT EXISTS", out)
        self.assertNotIn("CREATE OR REPLACE VIEW", out)
        self.assertIn("julianday", out)
        self.assertNotIn("TIMESTAMPDIFF", out)

    def test_mysql_keeps_timestampdiff(self):
        from botv.infra import schema
        import botv.infra.conn as conn

        orig = conn._resolve_backend
        conn._resolve_backend = lambda: "mysql"
        try:
            out = schema._adapt_view(schema.VIEWS["v_bot_meta"])
        finally:
            conn._resolve_backend = orig
        self.assertIn("TIMESTAMPDIFF", out)

    def test_view_has_no_index(self):
        """红线：视图里不能出现 KEY/INDEX"""
        from botv.infra import schema

        for name, ddl in schema.VIEWS.items():
            self.assertNotIn("KEY ", ddl.upper(), f"视图 {name} 不应有索引")


if __name__ == "__main__":
    unittest.main()
