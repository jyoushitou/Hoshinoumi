# ===================== 监护线程测试（v17.8） =====================

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


class TestPoolMonitor(unittest.TestCase):
    """一个线程看两个池：启动/停止、快照、告警"""

    def setUp(self):
        from bot.infra.monitor import PoolMonitor

        self.alerts = []
        self.M = PoolMonitor(interval=0.05, on_alert=self.alerts.append)

    def tearDown(self):
        self.M.stop()

    def test_snapshot_both_pools(self):
        snap = self.M.snapshot()
        self.assertIn("threads", snap)
        self.assertIn("db", snap)
        self.assertIn("ts", snap)

    def test_start_stop(self):
        self.assertFalse(self.M.running)
        self.M.start()
        self.assertTrue(self.M.running)
        self.M.stop()
        self.assertFalse(self.M.running)

    def test_start_idempotent(self):
        t1 = self.M.start()
        t2 = self.M.start()
        self.assertIs(t1, t2, "重复启动应复用同一线程")

    def test_beats_increase(self):
        self.M.start()
        time.sleep(0.2)
        self.assertGreaterEqual(self.M.stats()["beats"], 1)

    def test_alert_thread_queue(self):
        self.M._alert({"threads": {"size": 5, "queued": 10}, "db": {}})
        self.assertTrue(self.alerts)

    def test_alert_conn_leak(self):
        self.M._alert({"threads": {}, "db": {"idle": 0, "size": 6, "borrowed": 6}})
        self.assertIn("泄漏", self.alerts[0][0])

    def test_no_alert_when_healthy(self):
        self.M._alert({"threads": {"size": 5, "queued": 0},
                       "db": {"idle": 4, "size": 6, "borrowed": 2, "timeouts": 0}})
        self.assertEqual(self.alerts, [])

    def test_global_start_stop(self):
        from bot.infra import monitor

        monitor.stop_monitor()
        monitor.start_monitor(interval=0.05)
        try:
            self.assertTrue(monitor.get_monitor().running)
            self.assertIn("监护", monitor.describe())
        finally:
            monitor.stop_monitor()

    def test_default_pool_sizes(self):
        """v17.8：线程池 5 / 连接池 6"""
        from bot.infra.blocking import thread_stats
        from bot.infra.pool import ConnPool

        self.assertEqual(thread_stats()["size"], 5)
        self.assertEqual(ConnPool().size, 6)


if __name__ == "__main__":
    unittest.main()
