# ===================== 持久层解结测试（v17.14 债一·第一步） =====================

import os
import shutil
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


class TestConnInjection(unittest.TestCase):
    """注入配置后，conn 不再回头读 settings"""

    def setUp(self):
        from botv.infra import conn

        self.C = conn
        self.dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            ".tmp", f"inj-{os.getpid()}")
        shutil.rmtree(self.dir, ignore_errors=True)
        os.makedirs(self.dir, exist_ok=True)
        self._orig = (conn._config["backend"], conn._config["mysql"],
                      conn._config["sqlite_path"])

    def tearDown(self):
        self.C.configure(mysql_config=self._orig[1], backend=self._orig[0],
                         sqlite_path=self._orig[2])
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_configured_flag(self):
        self.C.configure(backend="sqlite", sqlite_path=os.path.join(self.dir, "a.db"))
        self.assertTrue(self.C.configured())

    def test_injected_backend_wins(self):
        """注入 sqlite 时，即使 settings 说 mysql 也用 sqlite"""
        self.C.configure(backend="sqlite", sqlite_path=os.path.join(self.dir, "a.db"))
        orig = sys.modules.get("botv.core.settings")
        self.assertEqual(self.C._resolve_backend(), "sqlite")

    def test_injected_path_used(self):
        path = os.path.join(self.dir, "b.db")
        self.C.configure(backend="sqlite", sqlite_path=path)
        self.assertEqual(self.C._resolve_sqlite_path(), path)

    def test_gives_cursor_without_settings(self):
        """注入后能用，且不需要 settings 参与"""
        self.C.configure(backend="sqlite", sqlite_path=os.path.join(self.dir, "c.db"))
        c = self.C.get_cursor()
        c.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY)")
        c.connection.commit()
        self.assertEqual(self.C._resolve_backend(), "sqlite")

    def test_configure_clears_thread_conn(self):
        """重新注入要作废旧连接，否则还连着老库"""
        self.C.configure(backend="sqlite", sqlite_path=os.path.join(self.dir, "d.db"))
        self.C.get_db()
        self.assertTrue(hasattr(self.C._local, "conn"))
        self.C.configure(backend="sqlite", sqlite_path=os.path.join(self.dir, "e.db"))
        self.assertFalse(hasattr(self.C._local, "conn"), "旧连接应作废")

    def test_mysql_config_injected(self):
        cfg = {"host": "h", "port": 1, "user": "u", "password": "p",
               "database": "d", "charset": "utf8mb4"}
        self.C.configure(mysql_config=cfg, backend="mysql")
        self.assertEqual(self.C._resolve_mysql()["host"], "h")


class TestBootstrapInjects(unittest.TestCase):
    """bootstrap 启动时应该注入一次"""

    def test_bootstrap_calls_configure(self):
        import inspect

        from botv.app import bootstrap

        src = inspect.getsource(bootstrap.bootstrap)
        self.assertIn("_configure_db", src, "bootstrap 必须先注入配置")

    def test_configure_db_returns_backend(self):
        from botv.app import bootstrap

        self.assertTrue(callable(bootstrap._configure_db))


if __name__ == "__main__":
    unittest.main()
