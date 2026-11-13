# ===================== v18.7 定时规则 =====================
# 覆盖：工作日/周末起床、明天工作日睡觉、晚餐 16:40、exact/habit 抖动、当天覆盖

import sys
import types
import unittest
from datetime import datetime
from unittest.mock import patch


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

from bot.schedule import cron  # noqa: E402


class _Rng:
    def __init__(self, value=0):
        self.value = value
        self.calls = []

    def randint(self, a, b):
        self.calls.append((a, b))
        return self.value


class TestRules(unittest.TestCase):
    def _wake(self, now):
        task = {"schedule_type": "daily", "rule": "wake", "timing": "habit",
                "jitter_min": 0, "target_id": "1", "content": "scene:催起床"}
        return cron.compute_next(task, now=now, use_overrides=False)

    def _sleep(self, now):
        task = {"schedule_type": "daily", "rule": "sleep", "timing": "habit",
                "jitter_min": 0, "target_id": "1", "content": "scene:催睡觉"}
        return cron.compute_next(task, now=now, use_overrides=False)

    def test_wake_workday(self):
        # 2026-11-13 周五
        self.assertEqual(self._wake(datetime(2026, 11, 13, 6, 0)),
                         datetime(2026, 11, 13, 7, 30))

    def test_wake_weekend(self):
        # 2026-11-14 周六
        self.assertEqual(self._wake(datetime(2026, 11, 14, 6, 0)),
                         datetime(2026, 11, 14, 8, 0))

    def test_sleep_before_workday(self):
        # 周日 2026-11-15 晚上，明天周一工作日 → 23:00
        self.assertEqual(self._sleep(datetime(2026, 11, 15, 22, 0)),
                         datetime(2026, 11, 15, 23, 0))

    def test_sleep_before_weekend(self):
        # 周五 2026-11-13 晚上，明天周六 → 23:30
        self.assertEqual(self._sleep(datetime(2026, 11, 13, 22, 0)),
                         datetime(2026, 11, 13, 23, 30))

    def test_dinner_1640(self):
        task = {"schedule_type": "daily", "at_time": "16:40", "timing": "exact",
                "jitter_min": 0, "target_id": "1", "content": "scene:提醒晚餐"}
        nxt = cron.compute_next(task, now=datetime(2026, 11, 13, 16, 0),
                                use_overrides=False)
        self.assertEqual(nxt, datetime(2026, 11, 13, 16, 40))

    def test_exact_no_jitter(self):
        task = {"schedule_type": "daily", "at_time": "16:40", "timing": "exact",
                "jitter_min": 10, "target_id": "1", "content": "scene:提醒晚餐"}
        nxt = cron.compute_next(task, now=datetime(2026, 11, 13, 16, 0),
                                use_overrides=False, rng=_Rng(10))
        self.assertEqual(nxt, datetime(2026, 11, 13, 16, 40))

    def test_habit_only_late(self):
        task = {"schedule_type": "daily", "at_time": "16:40", "timing": "habit",
                "jitter_min": 3, "target_id": "1", "content": "scene:提醒晚餐"}
        rng = _Rng(3)
        nxt = cron.compute_next(task, now=datetime(2026, 11, 13, 16, 0),
                                use_overrides=False, rng=rng)
        self.assertEqual(nxt, datetime(2026, 11, 13, 16, 43))
        self.assertEqual(rng.calls[0][0], 0, "habit 抖动下界必须是 0，不能提前")

    def test_override_at_time(self):
        task = {"schedule_type": "daily", "rule": "wake", "timing": "habit",
                "jitter_min": 0, "target_id": "1", "content": "scene:催起床"}

        def fake(tid, scene, day):
            return {"at_time": "07:40", "skip": 0} if day.isoformat() == "2026-11-13" else None

        with patch.object(cron, "get_override", fake):
            nxt = cron.compute_next(task, now=datetime(2026, 11, 13, 6, 0))
        self.assertEqual(nxt, datetime(2026, 11, 13, 7, 40))

    def test_override_skip(self):
        task = {"schedule_type": "daily", "rule": "wake", "timing": "habit",
                "jitter_min": 0, "target_id": "1", "content": "scene:催起床"}

        def fake(tid, scene, day):
            return {"at_time": None, "skip": 1} if day.isoformat() == "2026-11-13" else None

        with patch.object(cron, "get_override", fake):
            nxt = cron.compute_next(task, now=datetime(2026, 11, 13, 6, 0))
        self.assertEqual(nxt, datetime(2026, 11, 14, 8, 0), "跳过周五，周六 8:00")


class TestOverrides(unittest.TestCase):
    def setUp(self):
        from bot.schedule import extract
        self.E = extract
        self.now = datetime(2026, 11, 13, 6, 0)  # 周五

    def test_today_wake(self):
        ov = self.E.parse_override("今天 7:40 叫我", now=self.now)
        self.assertIsNotNone(ov)
        self.assertEqual(ov["scene"], "催起床")
        self.assertEqual(ov["day"].isoformat(), "2026-11-13")
        self.assertEqual(ov["at_time"], "07:40")
        self.assertFalse(ov["skip"])

    def test_tonight_sleep(self):
        ov = self.E.parse_override("今晚 11 点半睡", now=datetime(2026, 11, 13, 22, 0))
        self.assertIsNotNone(ov)
        self.assertEqual(ov["scene"], "催睡觉")
        self.assertEqual(ov["at_time"], "23:30")

    def test_tomorrow_skip(self):
        ov = self.E.parse_override("明天别叫我", now=self.now)
        self.assertIsNotNone(ov)
        self.assertEqual(ov["scene"], "催起床")
        self.assertEqual(ov["day"].isoformat(), "2026-11-14")
        self.assertTrue(ov["skip"])

    def test_daily_is_not_override(self):
        self.assertIsNone(self.E.parse_override("每天 7:30 叫我", now=self.now))


class TestNextSummary(unittest.TestCase):
    def test_next_summary(self):
        task = {"id": 1, "content": "scene:提醒晚餐",
                "next_ts": "2026-11-13 16:40:00", "enabled": 1}
        with patch.object(cron, "list_tasks", return_value=[task]), \
                patch.object(cron, "_now", return_value=datetime(2026, 11, 13, 12, 0)):
            out = cron.next_summary()
        self.assertIn("钩子 1 条", out)
        self.assertIn("16:40", out)
        self.assertIn("提醒晚餐", out)


if __name__ == "__main__":
    unittest.main()
