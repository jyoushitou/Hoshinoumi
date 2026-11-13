# ===================== 日志解耦测试（v17.14 债一·第二步） =====================

import io
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


class TestLogDecoupled(unittest.TestCase):
    """日志：文件优先，数据库异步刷；数据库挂了不影响日志"""

    def setUp(self):
        import bot.log as L

        self.L = L
        self.dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            ".tmp", f"log-{os.getpid()}")
        shutil.rmtree(self.dir, ignore_errors=True)
        os.makedirs(self.dir, exist_ok=True)
        os.environ["NAO_LOG_DIR"] = self.dir
        os.environ["NAO_LOG_TXT"] = "1"
        from bot.infra import txtlog

        self.T = txtlog
        txtlog._state.update({"day": None, "path": None, "size": 0, "inited": False})
        self._orig_writer = L._db_writer
        L.stop_flusher()

    def tearDown(self):
        self.L.stop_flusher()
        self.L._db_writer = self._orig_writer
        os.environ.pop("NAO_LOG_DIR", None)
        os.environ.pop("NAO_LOG_TXT", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def _file_text(self):
        names = [n for n in os.listdir(self.dir) if n.endswith(".log")]
        if not names:
            return ""
        with io.open(os.path.join(self.dir, names[0]), encoding="utf-8") as f:
            return f.read()

    def test_writes_file(self):
        self.L._db_writer = lambda: (lambda tag, m: None)
        self.L.log_system("解耦测试")
        self.assertIn("解耦测试", self._file_text())

    def test_db_down_does_not_raise(self):
        """刷库抛异常，日志调用不能抛"""

        def boom():
            raise RuntimeError("数据库不可用")

        self.L._db_writer = boom
        try:
            self.L.log_err("数据库挂了也要能记")
        except Exception as e:
            self.fail(f"日志不该抛异常: {e}")
        self.assertIn("数据库挂了", self._file_text())

    def test_flush_reaches_db_writer(self):
        got = []
        self.L._db_writer = lambda: (lambda tag, m: got.append((tag, m)))
        self.L.log_api("刷库这一条")
        for _ in range(30):
            if got:
                break
            time.sleep(0.02)
        self.assertTrue(got, "应刷进数据库")
        self.assertEqual(got[0][0], "接口")

    def test_queue_bounded_no_block(self):
        """队满不阻塞：丢最旧的，计数 dropped"""
        self.L._db_writer = lambda: (lambda tag, m: time.sleep(0.05))
        start = time.time()
        for i in range(3000):
            self.L.log_api(f"灌水 {i}")
        cost = time.time() - start
        self.assertLess(cost, 5, "写日志不该被数据库拖住")
        st = self.L.flush_stats()
        self.assertIn("dropped", st)

    def test_stats_shape(self):
        st = self.L.flush_stats()
        for k in ("dropped", "flushed", "failed", "pending"):
            self.assertIn(k, st)

    def test_flusher_is_daemon(self):
        self.L._db_writer = lambda: (lambda tag, m: None)
        self.L.log_api("起线程")
        t = self.L._flusher["thread"]
        self.assertIsNotNone(t)
        self.assertTrue(t.daemon, "刷库线程必须 daemon，不能挡住退出")


class TestNoImportCycle(unittest.TestCase):
    """log 不能在 import 时就依赖 db（只在刷库线程里按需导入）"""

    def test_no_top_level_db_import(self):
        import ast

        from bot import log as L

        path = L.__file__
        with io.open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read())

        offenders = []
        for node in tree.body:                    # 只看模块顶层
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if "db" == mod.split(".")[-1]:
                    offenders.append(mod)
            elif isinstance(node, ast.Import):
                for a in node.names:
                    if a.name.split(".")[-1] == "db":
                        offenders.append(a.name)
        self.assertEqual(offenders, [], f"顶层不该 import db：{offenders}")

    def test_db_writer_is_lazy(self):
        """写库函数是运行时才导入的"""
        from bot import log as L

        self.assertTrue(callable(L._db_writer))


if __name__ == "__main__":
    unittest.main()
