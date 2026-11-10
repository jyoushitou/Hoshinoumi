# ===================== 池状态测试（v17.0.2） =====================
# 线程池状态在 infra/blocking.py，连接池状态在 infra/pool.py，两者互不引用。

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


_stub_missing_deps()


class TestThreadStats(unittest.TestCase):
    """线程池状态只由 blocking.py 提供"""

    def test_thread_stats_shape(self):
        from botv.infra.blocking import thread_stats

        s = thread_stats()
        self.assertIn("size", s)
        self.assertIn("queued", s)
        self.assertEqual(s["size"], 3)

    def test_describe_threads(self):
        from botv.infra.blocking import describe_threads

        text = describe_threads()
        self.assertIn("线程池", text)

    def test_no_conn_leak_into_blocking(self):
        """blocking 模块不该导出连接池相关的名字"""
        import botv.infra.blocking as B

        self.assertFalse(hasattr(B, "pool_stats"))
        self.assertFalse(hasattr(B, "describe_pools"))


class TestConnStats(unittest.TestCase):
    """连接池状态只由 pool.py 提供"""

    def setUp(self):
        from botv.infra import pool as P

        self.P = P

        class FakeConn:
            open = True

            def ping(self, reconnect=False):
                pass

            def cursor(self):
                return None

            def close(self):
                pass

        self._orig = P._pool
        P.set_pool(P.ConnPool(size=2, timeout=0.1, connect=lambda: FakeConn()))

    def tearDown(self):
        self.P.set_pool(self._orig)

    def test_conn_stats_fields(self):
        s = self.P.conn_stats()
        for key in ("size", "idle", "borrowed", "reused", "timeouts"):
            self.assertIn(key, s)
        self.assertEqual(s["size"], 2)

    def test_describe_conns(self):
        text = self.P.describe_conns()
        self.assertIn("连接池", text)
        self.assertIn("空闲", text)


if __name__ == "__main__":
    unittest.main()
