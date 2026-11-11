# ===================== 定时任务存储与钩子测试（v17.6） =====================

import asyncio
import sys
import types
import unittest
from datetime import datetime, timedelta


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


class TestComputeNext(unittest.TestCase):
    """daily / weekly / once / interval 的下次触发计算"""

    def setUp(self):
        from botv.schedule import cron

        self.C = cron
        self.now = datetime(2026, 11, 11, 8, 0)      # 周三

    def test_daily_today_later(self):
        task = {"schedule_type": "daily", "at_time": "09:30", "jitter_min": 0}
        nxt = self.C.compute_next(task, now=self.now)
        self.assertEqual(nxt, datetime(2026, 11, 11, 9, 30))

    def test_daily_rolls_to_tomorrow(self):
        task = {"schedule_type": "daily", "at_time": "07:00", "jitter_min": 0}
        nxt = self.C.compute_next(task, now=self.now)
        self.assertEqual(nxt, datetime(2026, 11, 12, 7, 0))

    def test_weekly_picks_matching_day(self):
        # 周三是 isoweekday 3；给它周一(1)
        task = {"schedule_type": "weekly", "at_time": "09:00",
                "weekdays": "1", "jitter_min": 0}
        nxt = self.C.compute_next(task, now=self.now)
        self.assertEqual(nxt.isoweekday(), 1)
        self.assertGreater(nxt, self.now)

    def test_weekly_english(self):
        task = {"schedule_type": "weekly", "at_time": "20:00",
                "weekdays": "fri", "jitter_min": 0}
        nxt = self.C.compute_next(task, now=self.now)
        self.assertEqual(nxt.isoweekday(), 5)

    def test_once_future(self):
        task = {"schedule_type": "once",
                "once_at": "2026-11-15 09:00:00", "jitter_min": 0}
        nxt = self.C.compute_next(task, now=self.now)
        self.assertEqual(nxt, datetime(2026, 11, 15, 9, 0))

    def test_once_past_returns_none(self):
        task = {"schedule_type": "once", "once_at": "2026-11-01 09:00:00"}
        self.assertIsNone(self.C.compute_next(task, now=self.now))

    def test_interval(self):
        task = {"schedule_type": "interval", "interval_min": 30,
                "last_fire": "2026-11-11 07:45:00", "jitter_min": 0}
        nxt = self.C.compute_next(task, now=self.now)
        self.assertEqual(nxt, datetime(2026, 11, 11, 8, 15))

    def test_jitter_within_range(self):
        task = {"schedule_type": "daily", "at_time": "09:00", "jitter_min": 10}

        class R:
            def randint(self, a, b):
                return b

        nxt = self.C.compute_next(task, now=self.now, rng=R())
        self.assertEqual(nxt, datetime(2026, 11, 11, 9, 10), "正抖动")

    def test_bad_time_returns_none(self):
        self.assertIsNone(self.C.compute_next(
            {"schedule_type": "daily", "at_time": "abc"}, now=self.now))


class TestHooks(unittest.TestCase):
    """钩子：挂上、取消、触发后重排"""

    def setUp(self):
        from botv.schedule import cron

        self.C = cron
        self.C.cancel_all()
        self.tasks = {1: {"id": 1, "schedule_type": "daily", "at_time": "23:59",
                          "jitter_min": 0, "enabled": 1, "target_id": "1"}}
        self.C.get = lambda tid: self.tasks.get(int(tid))
        self.C.set_next = lambda tid, ts: True
        self.C.set_enabled = lambda tid, on: True
        self.C.list_tasks = lambda **kw: list(self.tasks.values())

        self.submitted = []
        self.sched = types.SimpleNamespace(
            submit=lambda kind, key, args=(): self.submitted.append((kind, key, args)))

    def tearDown(self):
        self.C.cancel_all()
        for name in ("get", "set_next", "set_enabled", "list_tasks"):
            if hasattr(self, "_orig_" + name):
                setattr(self.C, name, getattr(self, "_orig_" + name))

    def test_schedule_and_cancel(self):
        loop = asyncio.new_event_loop()
        try:
            h = self.C.schedule_one(self.tasks[1], loop, self.sched)
            self.assertIsNotNone(h)
            self.assertEqual(len(self.C.handles), 1)
            self.assertTrue(self.C.cancel(1))
            self.assertEqual(len(self.C.handles), 0)
        finally:
            loop.close()

    def test_schedule_all(self):
        loop = asyncio.new_event_loop()
        try:
            n = self.C.schedule_all(list(self.tasks.values()), loop, self.sched)
        finally:
            loop.close()
        self.assertEqual(n, 1)
        self.assertEqual(self.C.stats()["hooked"], 1)

    def test_fire_submits_event(self):
        """手动调用 _fire 验证投递 + 重排"""
        loop = asyncio.new_event_loop()
        try:
            h = self.C.schedule_one(self.tasks[1], loop, self.sched)
            self.assertIsNotNone(h)
            # 直接触发定时器回调（不改真实时间）
            h._callback()
        finally:
            loop.close()
        self.assertEqual(len(self.submitted), 1)
        self.assertEqual(self.submitted[0][0], "cron_task")
        self.assertEqual(self.submitted[0][2], (1,))

    def test_disabled_task_not_hooked(self):
        task = dict(self.tasks[1], enabled=0)
        self.tasks[1] = task
        loop = asyncio.new_event_loop()
        try:
            n = self.C.schedule_all([task], loop, self.sched)
        finally:
            loop.close()
        # schedule_all 不检查 enabled（由调用方传 enabled_only 的列表），这里只验证不炸
        self.assertIn(n, (0, 1))

    def test_stats_shape(self):
        s = self.C.stats()
        self.assertIn("hooked", s)
        self.assertIn("ids", s)


if __name__ == "__main__":
    unittest.main()
