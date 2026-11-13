# ===================== 统一时钟测试（v18.0 U1/U2） =====================

import sys
import types
import unittest
from datetime import datetime, timedelta, timezone


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


class TestClock(unittest.TestCase):
    """时钟必须固定东八区，不受服务器 TZ 影响"""

    def setUp(self):
        from bot.core import clock

        self.C = clock

    def test_now_is_cst(self):
        self.assertEqual(self.C.now().utcoffset(), timedelta(hours=8))

    def test_naive_is_cst_wall_clock(self):
        utc = datetime.now(timezone.utc).replace(tzinfo=None)
        diff = (self.C.naive() - utc).total_seconds() / 3600
        self.assertAlmostEqual(diff, 8, delta=0.1, msg="naive 应比 UTC 快 8 小时")

    def test_naive_has_no_tz(self):
        self.assertIsNone(self.C.naive().tzinfo)

    def test_today_matches_naive(self):
        self.assertEqual(self.C.today(), self.C.naive().date())

    def test_fmt(self):
        for fn in (self.C.fmt_hms, self.C.fmt_ymd, self.C.fmt_full):
            self.assertTrue(fn())
        self.assertEqual(len(self.C.fmt_hms()), 8)      # HH:MM:SS
        self.assertEqual(len(self.C.fmt_ymd()), 10)     # YYYY-MM-DD

    def test_to_naive_and_back(self):
        aware = self.C.now()
        naive = self.C.to_naive(aware)
        self.assertIsNone(naive.tzinfo)
        self.assertEqual(self.C.to_cst(naive).utcoffset(), timedelta(hours=8))

    def test_parse(self):
        dt = self.C.parse("2026-11-12 07:30:00")
        self.assertEqual(dt.year, 2026)
        self.assertIsNone(self.C.parse("不是时间"))

    def test_parse_roundtrip(self):
        dt = self.C.parse("2026-11-12 07:30:00")
        self.assertEqual(self.C.fmt_full(dt), "2026-11-12 07:30:00")


class TestCronUsesCst(unittest.TestCase):
    """cron 算下次触发要用东八区，否则整体偏 8 小时"""

    def test_cron_now_is_cst(self):
        from bot.schedule import cron

        diff = (cron._now() - datetime.now(timezone.utc).replace(tzinfo=None)).total_seconds() / 3600
        self.assertAlmostEqual(diff, 8, delta=0.1)

    def test_compute_next_daily(self):
        from bot.schedule import cron

        now = datetime(2026, 11, 12, 9, 0)
        task = {"schedule_type": "daily", "at_time": "07:30", "jitter_min": 0}
        self.assertEqual(cron.compute_next(task, now=now),
                         datetime(2026, 11, 13, 7, 30))

    def test_compute_next_tonight(self):
        from bot.schedule import cron

        now = datetime(2026, 11, 12, 9, 0)
        task = {"schedule_type": "daily", "at_time": "23:00", "jitter_min": 0}
        self.assertEqual(cron.compute_next(task, now=now),
                         datetime(2026, 11, 12, 23, 0))


class TestLogAndTxtlogUseCst(unittest.TestCase):
    """日志时间戳与按天文件名都用东八区"""

    def test_log_stamp(self):
        import bot.log as L

        self.assertRegex(L._stamp(), r"^\d\d:\d\d:\d\d$")

    def test_txtlog_dir_is_repo_root(self):
        """v18.0 U3：日志目录是仓库根，不是 bot/ 下面"""
        import os

        from bot.infra import txtlog

        d = txtlog._dir()
        root = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(txtlog.__file__))))
        self.assertEqual(d, os.path.join(root, "logs"))




class TestCustomClock(unittest.TestCase):
    """v18.0 U8：时区可配、可冻结、可偏移"""

    def setUp(self):
        from bot.core import clock

        self.C = clock
        clock.reset()

    def tearDown(self):
        self.C.reset()
        import os
        os.environ.pop("NAO_TZ", None)
        os.environ.pop("NAO_CLOCK_OFFSET", None)

    def test_default_label(self):
        self.assertIn("Asia/Shanghai", self.C.tz_label())
        self.assertIn("UTC+8", self.C.tz_label())

    def test_freeze_and_reset(self):
        import datetime as dt

        self.C.use_fake(dt.datetime(2026, 11, 12, 7, 30))
        self.assertEqual(self.C.fmt_full(), "2026-11-12 07:30:00")
        self.C.reset()
        self.assertNotEqual(self.C.fmt_full(), "2026-11-12 07:30:00")

    def test_offset_from_env(self):
        import os

        os.environ["NAO_CLOCK_OFFSET"] = "60"
        self.assertEqual(self.C.offset_minutes(), 60)

    def test_tz_name_from_env(self):
        import os

        os.environ["NAO_TZ"] = "Asia/Tokyo"
        self.assertEqual(self.C.tz_name(), "Asia/Tokyo")

    def test_invalid_tz_falls_back(self):
        import os

        os.environ["NAO_TZ"] = "Mars/Olympus"
        self.assertEqual(self.C.tz_label().split()[0], "Mars/Olympus")  # 名字照显
        self.assertEqual(self.C.now().utcoffset(), self.C.CST.utcoffset(None))  # 实际回 +8


class TestVersionShowsTimezone(unittest.TestCase):
    def test_version_line(self):
        from bot.core import version

        text = version.describe()
        self.assertIn("时区", text)
        self.assertIn("UTC+8", text)


if __name__ == "__main__":
    unittest.main()
