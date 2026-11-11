# ===================== 存储后端测试（v17.11） =====================

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


class TestBackendChoice(unittest.TestCase):
    """选后端：默认 mysql，配了 sqlite 就走 sqlite"""

    def setUp(self):
        from botv.core import settings

        self.S = settings
        settings._cache = None     # 每次测试重新读配置
        self._saved = {k: os.environ.get(k) for k in
                       ("NAO_DB_BACKEND", "NAO_DB_PATH", "NAO_DB_HOST")}
        self.dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            ".tmp", f"backend-{os.getpid()}")
        shutil.rmtree(self.dir, ignore_errors=True)
        os.makedirs(self.dir, exist_ok=True)

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        # 重置线程本地连接
        from botv.infra import conn

        conn._local.__dict__.clear()
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_auto_prefers_mysql(self):
        """auto 模式：MySQL 连得上就用 MySQL"""
        os.environ.pop("NAO_DB_BACKEND", None)
        self.S._backend_cache["value"] = None
        orig = self.S.mysql_reachable
        self.S.mysql_reachable = lambda timeout=3.0: True
        try:
            self.assertEqual(self.S.storage_backend(), "mysql")
        finally:
            self.S.mysql_reachable = orig
            self.S._backend_cache["value"] = None

    def test_auto_falls_back_to_sqlite(self):
        """auto 模式：MySQL 连不上 → 自动用 SQLite"""
        os.environ.pop("NAO_DB_BACKEND", None)
        self.S._backend_cache["value"] = None
        orig = self.S.mysql_reachable
        self.S.mysql_reachable = lambda timeout=3.0: False
        try:
            self.assertEqual(self.S.storage_backend(), "sqlite")
        finally:
            self.S.mysql_reachable = orig
            self.S._backend_cache["value"] = None

    def test_probe_result_cached(self):
        """探测只做一次（缓存），不会每次连库都试 MySQL"""
        os.environ.pop("NAO_DB_BACKEND", None)
        self.S._backend_cache["value"] = None
        calls = []
        orig = self.S.mysql_reachable
        self.S.mysql_reachable = lambda timeout=3.0: calls.append(1) or False
        try:
            self.S.storage_backend()
            self.S.storage_backend()
            self.S.storage_backend()
        finally:
            self.S.mysql_reachable = orig
            self.S._backend_cache["value"] = None
        self.assertEqual(len(calls), 1, "三次调用只探测一次")

    def test_explicit_mysql_no_probe(self):
        """显式配 mysql：即使连不上也不退（让报错暴露出来）"""
        os.environ["NAO_DB_BACKEND"] = "mysql"
        self.S._backend_cache["value"] = None
        self.assertEqual(self.S.storage_backend(), "mysql")

    def test_sqlite_aliases(self):
        for v in ("sqlite", "sqlite3", "file"):
            os.environ["NAO_DB_BACKEND"] = v
            self.assertEqual(self.S.storage_backend(), "sqlite")

    def test_unknown_treated_as_auto(self):
        """写错的值按 auto 处理：能连 MySQL 就用，否则 SQLite"""
        os.environ["NAO_DB_BACKEND"] = "postgres"
        self.S._backend_cache["value"] = None
        orig = self.S.mysql_reachable
        self.S.mysql_reachable = lambda timeout=3.0: False
        try:
            self.assertEqual(self.S.storage_backend(), "sqlite")
        finally:
            self.S.mysql_reachable = orig
            self.S._backend_cache["value"] = None

    def test_sqlite_path(self):
        os.environ["NAO_DB_PATH"] = os.path.join(self.dir, "x.db")
        self.assertEqual(self.S.sqlite_path(), os.path.join(self.dir, "x.db"))

    def test_crud_on_sqlite(self):
        """真连一次：建表 / 插入 / 查询 / 计数"""
        os.environ["NAO_DB_BACKEND"] = "sqlite"
        os.environ["NAO_DB_PATH"] = os.path.join(self.dir, "nao.db")
        from botv.infra import conn

        conn._local.__dict__.clear()
        c = conn.get_cursor()
        c.execute("CREATE TABLE t (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)")
        c.execute("INSERT INTO t(name) VALUES(%s)", ("奈绪",))
        c.connection.commit()
        c.execute("SELECT id, name FROM t")
        rows = c.fetchall()
        self.assertEqual(rows, [{"id": 1, "name": "奈绪"}], "应返回字典行")
        c.execute("SELECT COUNT(*) AS n FROM t")
        self.assertEqual(c.fetchone()["n"], 1)

    def test_placeholders_translated(self):
        """%s 要能翻译成 ?（多个参数也要对）"""
        os.environ["NAO_DB_BACKEND"] = "sqlite"
        os.environ["NAO_DB_PATH"] = os.path.join(self.dir, "p.db")
        from botv.infra import conn

        conn._local.__dict__.clear()
        c = conn.get_cursor()
        c.execute("CREATE TABLE t (a TEXT, b TEXT)")
        c.execute("INSERT INTO t(a,b) VALUES(%s,%s)", ("x", "y"))
        c.connection.commit()
        c.execute("SELECT a,b FROM t WHERE a=%s AND b=%s", ("x", "y"))
        self.assertEqual(c.fetchone(), {"a": "x", "b": "y"})

    def test_wal_enabled(self):
        os.environ["NAO_DB_BACKEND"] = "sqlite"
        os.environ["NAO_DB_PATH"] = os.path.join(self.dir, "w.db")
        from botv.infra import conn

        conn._local.__dict__.clear()
        c = conn.get_cursor()
        c.execute("PRAGMA journal_mode")
        mode = list(c.fetchone().values())[0]
        self.assertEqual(str(mode).lower(), "wal")


if __name__ == "__main__":
    unittest.main()
