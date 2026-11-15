# ===================== v26.6 模糊指令 =====================
import sys
import types
import unittest
from datetime import datetime

try:
    import jieba  # noqa: F401
except ImportError:
    m = types.ModuleType("jieba")
    m.lcut = lambda s: list(s)
    sys.modules["jieba"] = m

from bot.schedule import extract


class TestTimerNormalize(unittest.TestCase):
    NOW = datetime(2026, 11, 15, 18, 40, 0)

    def test_30min(self):
        got = extract.extract("提醒我过30min吃药", self.NOW)
        self.assertIsNotNone(got)
        self.assertEqual(got["schedule_type"], "once")
        self.assertEqual(got["content"], "吃药")
        self.assertEqual(got["once_at"], "2026-11-15 19:10:00")

    def test_30_minutes(self):
        got = extract.extract("提醒我过30 minutes吃药", self.NOW)
        self.assertIsNotNone(got)
        self.assertEqual(got["content"], "吃药")

    def test_command_hint_once(self):
        got = extract.extract("提醒我过30min吃药", self.NOW)
        hint = extract.command_hint(got)
        self.assertIn("!cron once", hint)
        self.assertIn("吃药", hint)

    def test_command_hint_daily(self):
        got = extract.extract("每天7点提醒我吃药", self.NOW)
        hint = extract.command_hint(got)
        self.assertIn("!cron add 07:00 daily", hint)

    def test_not_timer(self):
        self.assertIsNone(extract.extract("提醒我这件事很重要", self.NOW))


if __name__ == "__main__":
    unittest.main()
