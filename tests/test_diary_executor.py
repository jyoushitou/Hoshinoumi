# ===================== 日记执行器测试（v17.3） =====================

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
    def __init__(self, args=()):
        self.args = args
        self.kind = "diary_write"


class TestDiaryExecutor(unittest.TestCase):
    """日记走独立事件：tick 只投递，生成在 worker 里"""

    def setUp(self):
        import bot.executors.diary as D
        from bot.scheduler.dispatcher import Scheduler, set_scheduler

        self.D = D
        self.sched = Scheduler()
        set_scheduler(self.sched)
        import bot.schedule.runner as R

        self.R = R
        self._orig = R.generate_diary

    def tearDown(self):
        from bot.scheduler.dispatcher import set_scheduler

        self.R.generate_diary = self._orig
        set_scheduler(None)

    def test_registered(self):
        from bot.events import registry

        self.assertIsNotNone(registry.get("diary_write"))

    def test_generates(self):
        called = []

        async def fake(uid, day):
            called.append((uid, day))
            return "今天的日记"

        self.R.generate_diary = fake
        out = asyncio.run(self.D.handle_diary_write(_Ev(args=("2026-11-09",))))
        self.assertTrue(out["ok"])
        self.assertEqual(called[0][1], "2026-11-09")
        self.assertEqual(out["length"], len("今天的日记"))

    def test_missing_day(self):
        out = asyncio.run(self.D.handle_diary_write(_Ev(args=())))
        self.assertFalse(out["ok"])

    def test_failure_reports(self):
        async def boom(uid, day):
            raise RuntimeError("模型挂了")

        self.R.generate_diary = boom
        out = asyncio.run(self.D.handle_diary_write(_Ev(args=("2026-11-09",))))
        self.assertFalse(out["ok"])

    def test_submit_dedupe(self):
        self.assertTrue(self.D.submit("2026-11-09"))
        self.assertFalse(self.D.submit("2026-11-09"), "同一天不该重复投递")
        self.assertTrue(self.D.submit("2026-11-10"))

    def test_tick_submits_instead_of_awaiting(self):
        """3 点整：tick 只投递，不自己生成"""
        import bot.executors.ticker as T
        from bot.core import state as cfg
        from datetime import datetime

        from bot.config import CST

        called = []

        async def fake(uid, day):
            called.append(day)
            return "x"

        self.R.generate_diary = fake
        cfg.daily_trigger.clear()

        now = datetime(2026, 11, 10, 3, 0, tzinfo=CST)
        orig_now = T._now
        T._now = lambda: now
        try:
            asyncio.run(T.handle_minute_tick(_Ev()))
        finally:
            T._now = orig_now

        self.assertEqual(called, [], "tick 不该自己生成日记")
        self.assertEqual(self.sched.stats()["queue"]["event"] >= 0, True)


if __name__ == "__main__":
    unittest.main()
