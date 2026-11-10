# ===================== 连接池测试（v17.0.2） =====================

import sys
import threading
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


_stub_missing_deps()


class FakeConn:
    """假连接：记录 open/ping 行为"""

    def __init__(self, healthy=True):
        self.open = healthy
        self.pinged = 0
        self.closed = False

    def ping(self, reconnect=False):
        self.pinged += 1
        if not self.open:
            raise RuntimeError("连接已断")

    def cursor(self):
        return FakeCursor(self)

    def close(self):
        self.closed = True
        self.open = False


class FakeCursor:
    def __init__(self, conn):
        self.connection = conn
        self.closed = False

    def close(self):
        self.closed = True


class TestConnPool(unittest.TestCase):
    """连接池：复用、上限、断线重建、借还平衡"""

    def setUp(self):
        from botv.infra.pool import ConnPool

        self.created = []

        def make():
            c = FakeConn()
            self.created.append(c)
            return c

        self.pool = ConnPool(size=2, timeout=0.2, connect=make)

    def test_acquire_creates(self):
        conn = self.pool.acquire()
        self.assertIsNotNone(conn)
        self.assertEqual(len(self.created), 1)

    def test_release_and_reuse(self):
        c1 = self.pool.acquire()
        self.pool.release(c1)
        c2 = self.pool.acquire()
        self.assertIs(c1, c2, "归还后应复用同一条连接")
        self.assertEqual(self.pool.stats()["reused"], 1)

    def test_pool_limit_times_out(self):
        a = self.pool.acquire()
        b = self.pool.acquire()
        with self.assertRaises(TimeoutError):
            self.pool.acquire(timeout=0.1)
        self.pool.release(a)
        self.pool.release(b)
        self.assertEqual(self.pool.stats()["timeouts"], 1)

    def test_broken_connection_recreated(self):
        c1 = self.pool.acquire()
        c1.open = False               # 模拟连接断了
        self.pool.release(c1)         # 归还时应被丢弃
        c2 = self.pool.acquire()      # 再借应该是新连接
        self.assertIsNot(c1, c2)
        self.assertTrue(c2.open)

    def test_borrow_count_balanced(self):
        c1 = self.pool.acquire()
        self.assertEqual(self.pool.stats()["borrowed"], 1)
        self.pool.release(c1)
        self.assertEqual(self.pool.stats()["borrowed"], 0)

    def test_stats_shape(self):
        s = self.pool.stats()
        for key in ("size", "idle", "borrowed", "created", "reused", "timeouts"):
            self.assertIn(key, s)


class TestPooledCursor(unittest.TestCase):
    """with pooled_cursor 自动借还（异常也要还）"""

    def setUp(self):
        from botv.infra import pool as P

        self.P = P
        self.created = []

        def make():
            c = FakeConn()
            self.created.append(c)
            return c

        self.orig = P._pool
        P.set_pool(P.ConnPool(size=2, timeout=0.2, connect=make))

    def tearDown(self):
        self.P.set_pool(self.orig)

    def test_auto_release(self):
        from botv.infra.pool import pooled_cursor

        with pooled_cursor() as c:
            self.assertIsNotNone(c)
        self.assertEqual(self.P.get_pool().stats()["borrowed"], 0)

    def test_release_on_exception(self):
        from botv.infra.pool import pooled_cursor

        with self.assertRaises(ValueError):
            with pooled_cursor():
                raise ValueError("boom")
        self.assertEqual(self.P.get_pool().stats()["borrowed"], 0, "异常时也要归还")


if __name__ == "__main__":
    unittest.main()
