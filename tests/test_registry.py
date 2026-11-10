# ===================== 事件注册表测试（v17.1.0） =====================

import asyncio
import unittest


class TestRegistry(unittest.TestCase):
    """注册/查询/重复检测/默认参数继承"""

    def setUp(self):
        from botv.events import registry

        registry.clear()
        self.R = registry

    def tearDown(self):
        self.R.clear()

    def test_register_and_get(self):
        Priority = __import__("botv.events.base", fromlist=["Priority"]).Priority

        @self.R.register("idle_read", priority=Priority.IDLE, timeout=180)
        async def handler(ev):
            return "ok"

        h = self.R.get("idle_read")
        self.assertIsNotNone(h)
        self.assertIs(h.fn, handler)
        self.assertEqual(h.timeout, 180)
        self.assertEqual(h.priority, Priority.IDLE)

    def test_duplicate_raises(self):
        @self.R.register("dup")
        async def a(ev):
            return None

        with self.assertRaises(ValueError):
            @self.R.register("dup")
            async def b(ev):
                return None

    def test_require_missing(self):
        with self.assertRaises(KeyError):
            self.R.require("nope")

    def test_get_missing_returns_none(self):
        self.assertIsNone(self.R.get("nope"))

    def test_kinds_sorted(self):
        @self.R.register("b")
        async def b(ev):
            return None

        @self.R.register("a")
        async def a(ev):
            return None

        self.assertEqual(self.R.kinds(), ["a", "b"])

    def test_snapshot(self):
        from botv.events.base import Priority

        @self.R.register("chat", priority=Priority.CHAT, description="聊天")
        async def chat(ev):
            return None

        snap = self.R.snapshot()
        self.assertEqual(len(snap), 1)
        self.assertEqual(snap[0]["kind"], "chat")
        self.assertEqual(snap[0]["priority"], 0)
        self.assertEqual(snap[0]["description"], "聊天")

    def test_handler_runs(self):
        @self.R.register("run")
        async def run(ev):
            return 42

        h = self.R.require("run")
        self.assertEqual(asyncio.run(h.fn(None)), 42)

    def test_default_priority_and_timeout(self):
        from botv.events.base import DEFAULT_TIMEOUT, Priority

        @self.R.register("plain")
        async def plain(ev):
            return None

        h = self.R.require("plain")
        self.assertEqual(h.priority, Priority.IDLE)
        self.assertEqual(h.timeout, DEFAULT_TIMEOUT)


if __name__ == "__main__":
    unittest.main()
