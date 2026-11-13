# ===================== TXT 日志测试（v17.5） =====================

import os
import shutil
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


class TestTxtLog(unittest.TestCase):
    """写文件、追写、180 天清理、开关、异常不抛"""

    def setUp(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.dir = os.path.join(root, ".tmp", f"logtest-{os.getpid()}")
        shutil.rmtree(self.dir, ignore_errors=True)
        os.makedirs(self.dir, exist_ok=True)
        os.environ["NAO_LOG_DIR"] = self.dir
        os.environ["NAO_LOG_TXT"] = "1"
        os.environ["NAO_LOG_KEEP_DAYS"] = "180"

        from bot.infra import txtlog

        self.T = txtlog
        self.T._state.update({"day": None, "path": None, "size": 0, "inited": False})
        # 避免测试碰真数据库
        self._orig_purge = txtlog.purge_db_logs
        txtlog.purge_db_logs = lambda days=None: 0

    def tearDown(self):
        self.T.purge_db_logs = self._orig_purge
        os.environ.pop("NAO_LOG_DIR", None)
        os.environ.pop("NAO_LOG_TXT", None)
        os.environ.pop("NAO_LOG_KEEP_DAYS", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_write_creates_file(self):
        self.assertTrue(self.T.write("系统", "启动测试"))
        files = os.listdir(self.dir)
        self.assertEqual(len(files), 1)
        content = open(os.path.join(self.dir, files[0]), encoding="utf-8").read()
        self.assertIn("启动测试", content)
        self.assertIn("|系统|", content)

    def test_append_not_overwrite(self):
        self.T.write("系统", "第一行")
        self.T.write("接口", "第二行")
        name = os.listdir(self.dir)[0]
        content = open(os.path.join(self.dir, name), encoding="utf-8").read()
        self.assertEqual(content.count("\n"), 2)

    def test_disabled(self):
        os.environ["NAO_LOG_TXT"] = "0"
        self.assertFalse(self.T.write("系统", "不该写"))
        self.assertEqual(os.listdir(self.dir), [])

    def test_keep_days_default_180(self):
        os.environ.pop("NAO_LOG_KEEP_DAYS", None)
        self.assertEqual(self.T.keep_days(), 180, "默认半年")
        os.environ["NAO_LOG_KEEP_DAYS"] = "abc"
        self.assertEqual(self.T.keep_days(), 180, "非法值回落 180")

    def test_cleanup_old_files(self):
        old = os.path.join(self.dir, "nao-2020-01-01.log")
        today = os.path.join(self.dir, "nao-" + time.strftime("%Y-%m-%d") + ".log")
        for p in (old, today):
            open(p, "w", encoding="utf-8").write("x")
        removed = self.T.cleanup()
        self.assertEqual(removed, 1)
        self.assertFalse(os.path.exists(old))
        self.assertTrue(os.path.exists(today))

    def test_cleanup_keeps_recent(self):
        recent = os.path.join(self.dir, "nao-" + time.strftime("%Y-%m-%d") + ".log")
        open(recent, "w", encoding="utf-8").write("x")
        self.assertEqual(self.T.cleanup(), 0)

    def test_stats_and_describe(self):
        self.T.write("系统", "x")
        s = self.T.stats()
        self.assertEqual(s["files"], 1)
        self.assertEqual(s["keep_days"], 180)
        self.assertIn("文件日志", self.T.describe())

    def test_bad_dir_does_not_raise(self):
        os.environ["NAO_LOG_DIR"] = "/proc/不可能写入的目录"
        self.assertFalse(self.T.write("系统", "x"))

    def test_purge_db_logs_batches(self):
        import bot.infra.conn as conn

        class Cur:
            def __init__(self):
                self.calls = 0
                self.sqls = []
            def execute(self, sql, args=None):
                self.calls += 1
                self.sqls.append((sql, args))
                self.rowcount = 1000 if self.calls < 3 else 0
            connection = types.SimpleNamespace(commit=lambda: None)
            def close(self):
                pass

        cur = Cur()
        orig = conn.get_cursor
        conn.get_cursor = lambda: cur
        txtlog_mod = self.T
        txtlog_mod.purge_db_logs = self._orig_purge   # 换成真函数
        try:
            n = txtlog_mod.purge_db_logs(180)
        finally:
            conn.get_cursor = orig
        self.assertGreaterEqual(n, 2000)
        self.assertEqual(cur.sqls[0][1], (180,))

    def test_log_module_calls_txt(self):
        import bot.log as L

        written = []
        orig = self.T.write
        self.T.write = lambda tag, m: written.append((tag, m)) or True
        try:
            L.log_system("测试系统日志")
            L.log_err("测试异常")
        finally:
            self.T.write = orig
        self.assertEqual(len(written), 2)
        self.assertEqual(written[0][0], "系统")


if __name__ == "__main__":
    unittest.main()
