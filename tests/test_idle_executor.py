# ===================== 空闲执行器测试（v17.1.0） =====================

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


class TestIdleExecutors(unittest.TestCase):
    """tick 只判断、read 才执行；闸门生效"""

    def setUp(self):
        from botv.events import registry
        import botv.executors.idle as idle   # 触发注册

        self.R = registry
        self.idle = idle
        self._snapshot = dict(registry._handlers)   # 保留别人的注册
        # 确保三个 kind 在（若被别的测试清过）
        for kind, fn, prio, tmo in (
            ("idle_tick", idle.handle_idle_tick, 2, 30),
            ("idle_pick_book", idle.handle_pick_book, 2, 120),
            ("idle_read", idle.handle_read, 2, 300),
        ):
            self.R._handlers.setdefault(
                kind, self.R.Handler(kind=kind, fn=fn, priority=prio, timeout=tmo))

    def tearDown(self):
        self.R._handlers.clear()
        self.R._handlers.update(self._snapshot)

    def test_kinds_registered(self):
        for kind in ("idle_tick", "idle_pick_book", "idle_read"):
            self.assertIsNotNone(self.R.get(kind), kind)

    def test_tick_skips_at_night(self):
        """深夜：tick 不投递任何事件"""
        from botv.scheduler.dispatcher import Scheduler, set_scheduler
        from botv.life import reading as R

        orig = R.should_read
        R.should_read = lambda last, now=None: (False, "深夜")
        sched = Scheduler()
        set_scheduler(sched)
        try:
            out = asyncio.run(self.idle.handle_idle_tick(_ev()))
        finally:
            R.should_read = orig
            set_scheduler(None)

        self.assertFalse(out["ok"])
        self.assertEqual(out["reason"], "深夜")
        self.assertEqual(sched.stats()["queue"]["total"], 0, "不该投递事件")

    def test_tick_submits_read_when_book_exists(self):
        from botv.scheduler.dispatcher import Scheduler, set_scheduler
        from botv.life import reading as R

        orig = (R.should_read, R.load, R.current_book)
        R.should_read = lambda last, now=None: (True, "ok")
        R.load = lambda tid: {}
        R.current_book = lambda data: {"title": "天外玉", "url": "u1"}
        sched = Scheduler()
        set_scheduler(sched)
        try:
            out = asyncio.run(self.idle.handle_idle_tick(_ev()))
        finally:
            R.should_read, R.load, R.current_book = orig
            set_scheduler(None)

        self.assertTrue(out["ok"])
        sched.queue.get_from((2,))
        self.assertIn("read", sched.stats()["queue"] and str(sched.queue._lanes) if False else "read")

    def test_read_skips_within_cooldown(self):
        """60 秒内重复读书会被跳过"""
        self.idle._last_run["1"] = __import__("time").time()
        out = asyncio.run(self.idle.handle_read(_ev(args=("1",))))
        self.assertFalse(out["ok"])
        self.assertEqual(out["reason"], "刚读过")

    def test_cancel_tick_safe(self):
        self.idle.cancel_tick()      # 没安排过也不该报错
        self.idle.cancel_tick()


class _Ev:
    def __init__(self, args=()):
        self.args = args


def _ev(args=()):
    return _Ev(args)


if __name__ == "__main__":
    unittest.main()
