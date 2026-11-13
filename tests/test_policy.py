# ===================== 调度策略测试（v17.1.0） =====================

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


_stub_missing_deps()


class TestRetryDelay(unittest.TestCase):
    """退避：2, 4, 8, 16… 封顶 30"""

    def test_progression(self):
        from bot.scheduler.policy import retry_delay

        self.assertEqual(retry_delay(1), 2.0)
        self.assertEqual(retry_delay(2), 4.0)
        self.assertEqual(retry_delay(3), 8.0)
        self.assertEqual(retry_delay(4), 16.0)

    def test_cap(self):
        from bot.scheduler.policy import retry_delay

        self.assertLessEqual(retry_delay(10), 30.0)

    def test_zero_attempt(self):
        from bot.scheduler.policy import retry_delay

        self.assertEqual(retry_delay(0), 0.0)


class TestShouldRetry(unittest.TestCase):
    """超时不重试；次数用完不重试；其余可重试"""

    def _ev(self, retries=1):
        from bot.events.base import Event

        async def noop():
            return None

        return Event(kind="k", key="x", fn=noop, retries=retries)

    def test_timeout_not_retried(self):
        from bot.scheduler.policy import should_retry

        self.assertFalse(should_retry(self._ev(3), asyncio.TimeoutError(), 1))

    def test_normal_error_retried(self):
        from bot.scheduler.policy import should_retry

        self.assertTrue(should_retry(self._ev(2), RuntimeError("x"), 1))

    def test_exhausted(self):
        from bot.scheduler.policy import should_retry

        ev = self._ev(1)
        self.assertFalse(should_retry(ev, RuntimeError("x"), 1))

    def test_zero_retries(self):
        from bot.scheduler.policy import should_retry

        self.assertFalse(should_retry(self._ev(0), RuntimeError("x"), 1))


class TestClassify(unittest.TestCase):
    def test_kinds(self):
        from bot.scheduler.policy import classify

        self.assertEqual(classify(asyncio.TimeoutError()), "timeout")
        self.assertEqual(classify(ValueError("x")), "bad_input")
        self.assertEqual(classify(RuntimeError("x")), "error")


class TestBreaker(unittest.TestCase):
    """熔断：连续 3 次失败 → 停 1 小时 → 自动恢复"""

    def setUp(self):
        from bot.scheduler.policy import Breaker

        self.B = Breaker()

    def test_starts_closed(self):
        self.assertFalse(self.B.is_open("read"))
        self.assertEqual(self.B.remaining("read"), 0.0)

    def test_opens_after_threshold(self):
        self.assertFalse(self.B.record_failure("read"))
        self.assertFalse(self.B.record_failure("read"))
        self.assertTrue(self.B.record_failure("read"), "第 3 次应触发熔断")
        self.assertTrue(self.B.is_open("read"))

    def test_success_resets(self):
        self.B.record_failure("read")
        self.B.record_failure("read")
        self.B.record_success("read")
        self.assertEqual(self.B.failures("read"), 0)
        self.assertFalse(self.B.record_failure("read"), "清零后第一次不该熔断")

    def test_auto_recover_after_cooldown(self):
        import time

        now = time.time()
        for _ in range(3):
            self.B.record_failure("read", now=now)
        self.assertTrue(self.B.is_open("read", now=now))
        self.assertFalse(self.B.is_open("read", now=now + 3601), "1 小时后应恢复")

    def test_remaining(self):
        import time

        now = time.time()
        for _ in range(3):
            self.B.record_failure("read", now=now)
        left = self.B.remaining("read", now=now)
        self.assertAlmostEqual(left, 3600, delta=5)

    def test_per_kind_isolated(self):
        for _ in range(3):
            self.B.record_failure("read")
        self.assertTrue(self.B.is_open("read"))
        self.assertFalse(self.B.is_open("video"), "不同 kind 互不影响")

    def test_stats(self):
        for _ in range(3):
            self.B.record_failure("read")
        s = self.B.stats()
        self.assertIn("read", s["open_kinds"])
        self.assertEqual(s["total_open"], 1)


if __name__ == "__main__":
    unittest.main()
