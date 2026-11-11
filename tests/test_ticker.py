# ===================== 心跳 tick 测试（v17.3 U3） =====================

import asyncio
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


class _Ev:
    args = ()
    kind = "minute_tick"


class TestTicker(unittest.TestCase):
    """注册、跨天初始化、代码模式超时、场景派发"""

    def setUp(self):
        import botv.executors.ticker as T
        from botv.scheduler.dispatcher import Scheduler, set_scheduler

        self.T = T
        self.sched = Scheduler()
        set_scheduler(self.sched)
        T._state["day"] = None
        T._state["count"] = 0
        T._state["last_due"] = 0.0
        from botv.core import state as cfg

        cfg.daily_trigger.clear()
        cfg.task_trigger_minute.clear()
        self.cfg = cfg

    def tearDown(self):
        from botv.scheduler.dispatcher import set_scheduler

        set_scheduler(None)
        self.cfg.CODE_MODE = False

    def test_registered(self):
        from botv.events import registry

        self.assertIsNotNone(registry.get("minute_tick"))

    def test_cross_day_initializes(self):
        out = asyncio.run(self.T.handle_minute_tick(_Ev()))
        self.assertTrue(out["ok"])
        self.assertIsNotNone(self.T._state["day"], "跨天应记录日期")
        self.assertGreater(len(self.cfg.task_trigger_minute), 0, "应算出任务时刻")

    def test_code_mode_timeout(self):
        import time

        self.cfg.CODE_MODE = True
        self.cfg.CODE_MODE_LAST_MSG_TIME = time.time() - self.cfg.CODE_MODE_TIMEOUT - 5
        asyncio.run(self.T.handle_minute_tick(_Ev()))
        self.assertFalse(self.cfg.CODE_MODE, "超时应退出代码模式")

    def test_stats(self):
        asyncio.run(self.T.handle_minute_tick(_Ev()))
        s = self.T.stats()
        self.assertEqual(s["count"], 1)
        self.assertIn("interval", s)

    def test_cancel_safe(self):
        self.T.cancel_tick()
        self.T.cancel_tick()


if __name__ == "__main__":
    unittest.main()
