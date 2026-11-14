# ===================== v21.3 启动只校验 schema =====================
import sys
import types
import unittest
from unittest.mock import patch


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
    try:
        import jieba  # noqa: F401
    except ImportError:
        module("jieba", lcut=lambda s: list(s))
    try:
        import PIL  # noqa: F401
    except ImportError:
        module("PIL", Image=None)


_stub_missing_deps()


class _Cursor:
    def __init__(self, row):
        self.row = row

    def execute(self, *args, **kwargs):
        return self

    def fetchone(self):
        return self.row


class TestBootstrapSchema(unittest.TestCase):
    def test_version_ok(self):
        from bot.app import bootstrap

        with patch.object(bootstrap, "get_cursor", return_value=_Cursor({"v": "23"})):
            bootstrap._check_schema()

    def test_version_missing_raises(self):
        from bot.app import bootstrap

        with patch.object(bootstrap, "get_cursor", return_value=_Cursor({"v": "18"})):
            with self.assertRaises(RuntimeError):
                bootstrap._check_schema()

    def test_db_error_raises_migrate_hint(self):
        from bot.app import bootstrap

        with patch.object(bootstrap, "get_cursor", side_effect=RuntimeError("no table")):
            with self.assertRaises(RuntimeError) as ctx:
                bootstrap._check_schema()
        self.assertIn("migrate.py --apply", str(ctx.exception))

    def test_no_startup_ddl_functions(self):
        from bot.app import bootstrap

        self.assertFalse(hasattr(bootstrap, "_ensure_tables"))
        self.assertFalse(hasattr(bootstrap, "_ensure_cron_schema"))


if __name__ == "__main__":
    unittest.main()
