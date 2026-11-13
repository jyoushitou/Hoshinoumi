# ===================== 对话提取定时任务测试（v17.7） =====================

import sys
import types
import unittest
from datetime import datetime


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


class TestExtract(unittest.TestCase):
    """从聊天里提取定时任务"""

    def setUp(self):
        from botv.schedule import extract as E

        self.E = E
        self.now = datetime(2026, 11, 11, 9, 0)      # 周三 9 点

    def test_tomorrow_morning(self):
        d = self.E.extract("明天七点叫我", self.now)
        self.assertEqual(d["schedule_type"], "once")
        self.assertEqual(d["once_at"], "2026-11-12 07:00:00")

    def test_every_night_eleven(self):
        d = self.E.extract("每晚十一点提醒我睡觉", self.now)
        self.assertEqual(d["schedule_type"], "daily")
        self.assertEqual(d["at_time"], "23:00")
        self.assertIn("睡觉", d["content"])

    def test_evening_converts_pm(self):
        """「晚上八点」= 20:00（没说每天 → 一次性）"""
        d = self.E.extract("晚上八点提醒我吃药", self.now)
        self.assertEqual(d["schedule_type"], "once")
        self.assertEqual(d["once_at"], "2026-11-11 20:00:00")
        self.assertIn("吃药", d["content"])

    def test_weekly_without_hour_uses_default(self):
        d = self.E.extract("周五提醒我交报告", self.now)
        self.assertEqual(d["schedule_type"], "weekly")
        self.assertEqual(d["weekdays"], "5")
        self.assertEqual(d["at_time"], "09:00")
        self.assertEqual(d["content"], "交报告")

    def test_next_week_strips_prefix(self):
        d = self.E.extract("下周三提醒我开会", self.now)
        self.assertEqual(d["weekdays"], "3")
        self.assertEqual(d["content"], "开会", "「下」不该留在内容里")

    def test_relative_minutes_arabic(self):
        d = self.E.extract("30分钟后提醒我关火", self.now)
        self.assertEqual(d["once_at"], "2026-11-11 09:30:00")
        self.assertEqual(d["content"], "关火")

    def test_relative_minutes_chinese(self):
        d = self.E.extract("三十分钟后提醒我关火", self.now)
        self.assertEqual(d["once_at"], "2026-11-11 09:30:00")

    def test_half_hour(self):
        d = self.E.extract("半小时后提醒我喝水", self.now)
        self.assertEqual(d["once_at"], "2026-11-11 09:30:00")

    def test_no_action_word_returns_none(self):
        self.assertIsNone(self.E.extract("明天七点天气怎么样", self.now))

    def test_no_time_returns_none(self):
        self.assertIsNone(self.E.extract("提醒我买牛奶", self.now))

    def test_garbage_returns_none(self):
        self.assertIsNone(self.E.extract("今天好累", self.now))
        self.assertIsNone(self.E.extract("", self.now))

    def test_half_past(self):
        d = self.E.extract("七点半叫我起床", self.now)
        self.assertEqual(d["once_at"], "2026-11-12 07:30:00")

    def test_colon_format(self):
        d = self.E.extract("明天 7:30 叫我", self.now)
        self.assertEqual(d["once_at"], "2026-11-12 07:30:00")

    def test_should_extract_only_master_private(self):
        self.assertTrue(self.E.should_extract("private", "明天七点叫我", "1", "1"))
        self.assertFalse(self.E.should_extract("group", "明天七点叫我", "1", "1"))
        self.assertFalse(self.E.should_extract("private", "明天七点叫我", "2", "1"))
        self.assertFalse(self.E.should_extract("private", "!cron", "1", "1"))

    def test_dedupe(self):
        self.E._recent.clear()
        self.assertTrue(self.E.dedupe_ok("喝水"))
        self.assertFalse(self.E.dedupe_ok("喝水"), "5 分钟内同内容只建一次")

    def test_create_from_text(self):
        self.E._recent.clear()
        added = {}

        def fake_add(uid, st, content, **kw):
            added.update({"uid": uid, "type": st, "content": content, **kw})
            return 42

        tid, data = self.E.create_from_text(
            "明天七点提醒我喝水", "822891053", now=self.now, add_func=fake_add)
        self.assertEqual(tid, 42)
        self.assertEqual(added["type"], "once")
        self.assertEqual(added["source"], "chat")
        self.assertEqual(added["uid"], "822891053")



    def test_describe_daily(self):
        d = self.E.extract("每晚十一点提醒我睡觉", self.now)
        text = self.E.describe(d, 7)
        self.assertIn("每天 23:00", text)
        self.assertIn("睡觉", text)
        self.assertIn("!cron del 7", text, "要告诉她怎么撤")

    def test_describe_weekly(self):
        d = self.E.extract("周五提醒我交报告", self.now)
        text = self.E.describe(d, 3)
        self.assertIn("每周五", text)
        self.assertIn("09:00", text)

    def test_describe_once(self):
        d = self.E.extract("明天七点叫我", self.now)
        self.assertIn("2026-11-12 07:00", self.E.describe(d, 1))

if __name__ == "__main__":
    unittest.main()
