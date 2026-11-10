# ===================== 调度器入口测试（v17.1.0） =====================

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


class TestScheduler(unittest.TestCase):
    """投递、继承默认值、未注册报错、去重、统计"""

    def setUp(self):
        from botv.events import registry
        from botv.scheduler.dispatcher import Scheduler

        registry.clear()
        self.R = registry
        self.S = Scheduler(idle_workers=1, event_workers=1)
        self.ran = []

        @registry.register("demo", priority=2, timeout=1.0)
        async def demo(ev):
            self.ran.append(getattr(ev, "id", "?"))
            return "ok"

    def tearDown(self):
        self.R.clear()

    def test_submit_requires_registered_kind(self):
        with self.assertRaises(KeyError):
            self.S.submit("nope", "k1")

    def test_submit_and_run(self):
        async def main():
            self.S.start()
            ok = self.S.submit("demo", "k1")
            await asyncio.sleep(0.25)
            await self.S.stop()
            return ok

        self.assertTrue(asyncio.run(main()))
        self.assertEqual(len(self.ran), 1)
        self.assertEqual(self.S.stats()["done"], 1)

    def test_priority_inherited_from_registry(self):
        from botv.events.base import Priority

        @self.R.register("chatty", priority=Priority.CHAT, timeout=5)
        async def chatty(ev):
            return None

        self.S.submit("chatty", "c1")
        s = self.S.stats()
        self.assertEqual(s["queue"]["chat"], 1)
        self.assertEqual(s["queue"]["idle"], 0)

    def test_priority_override(self):
        from botv.events.base import Priority

        self.S.submit("demo", "k2", priority=Priority.CHAT)
        self.assertEqual(self.S.stats()["queue"]["chat"], 1)

    def test_dedupe(self):
        self.assertTrue(self.S.submit("demo", "same"))
        self.assertFalse(self.S.submit("demo", "same"), "同 key 未完成应丢弃")

    def test_stats_shape(self):
        s = self.S.stats()
        for key in ("running", "done", "failed", "queue", "kinds", "started"):
            self.assertIn(key, s)
        self.assertFalse(s["started"])

    def test_describe_lines(self):
        text = self.S.describe()
        self.assertIn("调度", text)
        self.assertIn("队列", text)


if __name__ == "__main__":
    unittest.main()
