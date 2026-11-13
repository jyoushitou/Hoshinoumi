# ===================== 元数据与 uptime 测试（v18.5） =====================
# 纪律：每个用例一个临时 SQLite 库，**绝不写 data/nao.db**
# （上一版就是没隔离，测试把版本号写进了真实库）。

import asyncio
import os
import shutil
import sys
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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


def _close_thread_conn(conn):
    """关掉当前线程的库连接再清缓存，不然 SQLite 连接会漏到 GC"""
    c = getattr(conn._local, "conn", None)
    try:
        if c is not None:
            c.close()
    except Exception:
        pass
    conn._local.__dict__.clear()


class _MetaDB(unittest.TestCase):
    """临时库夹具：每个用例独立，跑完删掉"""

    def setUp(self):
        from bot.core import settings

        self.dir = os.path.join(ROOT, ".tmp", f"meta-{os.getpid()}-{id(self)}")
        shutil.rmtree(self.dir, ignore_errors=True)
        os.makedirs(self.dir, exist_ok=True)
        self._old_env = (os.environ.get("NAO_DB_BACKEND"),
                         os.environ.get("NAO_DB_PATH"))
        os.environ["NAO_DB_BACKEND"] = "sqlite"
        os.environ["NAO_DB_PATH"] = os.path.join(self.dir, "nao.db")
        settings._cache = None
        settings._backend_cache["value"] = None

        from bot.infra import conn, schema

        conn._local.__dict__.clear()
        schema.ensure_tables()

    def tearDown(self):
        from bot.core import settings
        from bot.infra import conn

        _close_thread_conn(conn)
        for k, v in zip(("NAO_DB_BACKEND", "NAO_DB_PATH"), self._old_env):
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        settings._cache = None
        settings._backend_cache["value"] = None
        shutil.rmtree(self.dir, ignore_errors=True)


class TestRepoMeta(_MetaDB):
    """v18.5：启动时间存 bot_meta，不靠 logs 表"""

    def test_mark_start_idempotent(self):
        from bot.infra import repo_meta

        first = repo_meta.mark_start("18.5.0")
        again = repo_meta.mark_start("18.5.1")
        self.assertTrue(first)
        self.assertEqual(first, again, "首次启动时间不该被覆盖")
        self.assertEqual(repo_meta.get_value("version"), "18.5.1", "版本要跟着刷新")

    def test_first_start_ts_written(self):
        from bot.infra import repo_meta

        repo_meta.mark_start("18.5.0")
        ts = repo_meta.get_value("first_start_ts")
        self.assertTrue(ts and str(ts).isdigit(), f"应写入 epoch，实际 {ts!r}")

    def test_backfill_ts_for_old_db(self):
        """老库只有 first_start 字符串：启动时要补 epoch，视图才算得出来"""
        from bot.infra import repo_meta

        repo_meta.set_value("first_start", "2026-11-01 08:00:00")
        repo_meta.mark_start("18.5.0")
        self.assertTrue(repo_meta.get_value("first_start_ts"))
        info = repo_meta.uptime()
        self.assertIsNotNone(info)
        self.assertGreater(info["uptime_seconds"], 0)
        self.assertEqual(info["first_start"], "2026-11-01 08:00:00")

    def test_uptime_reads_view(self):
        from bot.infra import repo_meta

        repo_meta.mark_start("18.5.0")
        info = repo_meta.uptime()
        self.assertEqual(info["source"], "view", "正常情况必须走 v_bot_meta")
        self.assertEqual(info["version"], "18.5.0")
        self.assertGreaterEqual(info["uptime_seconds"], 0)
        self.assertEqual(info["days_since"], 0)

    def test_clear_logs_keeps_uptime(self):
        """验收（L6）：logs 清了，uptime 不变"""
        from bot.infra import conn, repo_meta

        repo_meta.mark_start("18.5.0")
        before = repo_meta.uptime()

        # 造一条 10 天前的日志：旧算法（MIN(created_at)）会算成 10 天
        c = conn.get_cursor()
        try:
            c.execute("INSERT INTO logs(level, message, created_at) "
                      "VALUES('INFO', '老日志', '2026-11-02 08:00:00')")
            c.connection.commit()
        finally:
            c.close()

        c = conn.get_cursor()
        try:
            c.execute("DELETE FROM logs")
            c.connection.commit()
        finally:
            c.close()

        after = repo_meta.uptime()
        self.assertEqual(before["first_start"], after["first_start"])
        self.assertLessEqual(abs(after["uptime_seconds"] - before["uptime_seconds"]), 2)
        self.assertEqual(after["days_since"], 0, "不该按日志算出 10 天")

    def test_uptime_text_format(self):
        from bot.infra import repo_meta

        repo_meta.mark_start("18.5.0")
        text, start = repo_meta.uptime_text()
        self.assertIn("天", text)
        self.assertIn("小时", text)
        self.assertIn("分钟", text)
        self.assertIsNotNone(start.year)

    def test_get_missing_returns_default(self):
        from bot.infra import repo_meta

        self.assertEqual(repo_meta.get_value("不存在的键", "默认"), "默认")

    def test_view_columns(self):
        from bot.infra import conn, repo_meta

        repo_meta.mark_start("18.5.0")
        c = conn.get_cursor()
        try:
            c.execute("SELECT * FROM v_bot_meta")
            row = c.fetchone()
        finally:
            c.close()
        for k in ("first_start", "first_start_ts", "version",
                  "uptime_seconds", "days_since"):
            self.assertIn(k, row)
        self.assertIsNotNone(row["uptime_seconds"])

    def test_meta_describe(self):
        from bot.infra import repo_meta

        repo_meta.mark_start("18.5.0")
        out = repo_meta.describe()
        self.assertIn("首次启动", out)
        self.assertIn("v_bot_meta", out)
        self.assertIn("18.5.0", out)


class TestCommands(_MetaDB):
    """!uptime / !meta 真的能出话"""

    def _ctx(self, name):
        from bot.cmd.registry import CommandContext

        return CommandContext(parts=[name], uid="10001", ws=None,
                              is_group=False, gid=0)

    def test_uptime_command(self):
        from bot.cmd import query
        from bot.infra import repo_meta

        repo_meta.mark_start("18.5.0")
        out = asyncio.run(query.cmd_uptime(self._ctx("uptime")))
        self.assertIn("运行时长", out)
        self.assertIn("首次启动", out)
        self.assertIn("v_bot_meta", out)

    def test_meta_command(self):
        from bot.cmd import query
        from bot.infra import repo_meta

        repo_meta.mark_start("18.5.0")
        out = asyncio.run(query.cmd_meta(self._ctx("meta")))
        self.assertIn("元数据", out)
        self.assertIn("首次启动", out)


class TestViews(unittest.TestCase):
    """v18.5：视图方言适配 + 老视图会被重建"""

    def _adapt(self, backend):
        import bot.infra.conn as conn
        from bot.infra import schema

        orig = conn._resolve_backend
        conn._resolve_backend = lambda: backend
        try:
            return schema._adapt_view(schema.VIEWS["v_bot_meta"])
        finally:
            conn._resolve_backend = orig

    def test_sqlite_adapt(self):
        out = self._adapt("sqlite")
        self.assertIn("CREATE VIEW IF NOT EXISTS", out)
        self.assertNotIn("CREATE OR REPLACE VIEW", out)
        self.assertIn("julianday", out)
        self.assertNotIn("UNIX_TIMESTAMP", out)
        self.assertNotIn("UNSIGNED", out)
        self.assertNotIn("TIMESTAMPDIFF", out)
        # _SQLiteCursor 会把 %s 当占位符换掉，视图 SQL 里绝不能出现
        self.assertNotIn("%s", out)

    def test_mysql_keeps_epoch_math(self):
        out = self._adapt("mysql")
        self.assertIn("UNIX_TIMESTAMP", out)
        self.assertIn("AS UNSIGNED", out)
        self.assertIn("AS SIGNED", out)

    def test_view_has_no_index(self):
        """红线：视图里不能出现 KEY/INDEX"""
        from bot.infra import schema

        for name, ddl in schema.VIEWS.items():
            self.assertNotIn("KEY ", ddl.upper(), f"视图 {name} 不应有索引")

    def test_old_view_recreated(self):
        """老库里已有旧视图时，ensure_tables 要换成新定义"""
        import os
        import shutil

        from bot.core import settings

        d = os.path.join(ROOT, ".tmp", f"view-{os.getpid()}")
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d, exist_ok=True)
        old_env = (os.environ.get("NAO_DB_BACKEND"), os.environ.get("NAO_DB_PATH"))
        os.environ["NAO_DB_BACKEND"] = "sqlite"
        os.environ["NAO_DB_PATH"] = os.path.join(d, "nao.db")
        settings._cache = None
        settings._backend_cache["value"] = None

        from bot.infra import conn, schema

        conn._local.__dict__.clear()
        try:
            schema.ensure_tables()
            c = conn.get_cursor()
            try:
                # 模拟 v18.5 早期版本的旧视图（只有 uptime_seconds）
                c.execute("DROP VIEW IF EXISTS v_bot_meta")
                c.execute("CREATE VIEW v_bot_meta AS SELECT "
                          "(SELECT v FROM bot_meta WHERE k='first_start') "
                          "AS first_start")
                c.connection.commit()
            finally:
                c.close()

            schema.ensure_tables()   # 再跑一次应把视图升级掉

            c = conn.get_cursor()
            try:
                c.execute("SELECT * FROM v_bot_meta")
                row = c.fetchone()
            finally:
                c.close()
            self.assertIn("days_since", row)
            self.assertIn("first_start_ts", row)
        finally:
            _close_thread_conn(conn)
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
