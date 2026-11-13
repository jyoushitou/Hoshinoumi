# ===================== 连发合并测试（v17.3 U2） =====================

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


class TestCoalescer(unittest.TestCase):
    """连发合并、单条不变、窗口上限、目标隔离"""

    def setUp(self):
        from bot.chat.coalesce import Coalescer

        self.got = []

        async def handler(target, items):
            self.got.append((target, list(items)))

        self.C = Coalescer(handler, debounce=0.05, window=0.2, max_items=3)

    def test_single_flushes_after_debounce(self):
        async def main():
            await self.C.offer("1", "在吗")
            await asyncio.sleep(0.1)

        asyncio.run(main())
        self.assertEqual(self.got, [("1", ["在吗"])])
        self.assertEqual(self.C.stats()["merged"], 0)

    def test_burst_merges(self):
        async def main():
            await self.C.offer("1", "在吗")
            await asyncio.sleep(0.01)
            await self.C.offer("1", "问你个事")
            await asyncio.sleep(0.01)
            await self.C.offer("1", "那个…")
            await asyncio.sleep(0.15)

        asyncio.run(main())
        self.assertEqual(len(self.got), 1, "连发应只处理一次")
        self.assertEqual(self.got[0][1], ["在吗", "问你个事", "那个…"])
        self.assertEqual(self.C.stats()["merged"], 2)

    def test_max_items_flushes_early(self):
        async def main():
            for i in range(3):
                await self.C.offer("1", f"第{i}句")
            await asyncio.sleep(0.02)

        asyncio.run(main())
        self.assertEqual(len(self.got), 1)
        self.assertEqual(len(self.got[0][1]), 3)
        self.assertEqual(self.C.stats()["pending"], 0)

    def test_targets_isolated(self):
        async def main():
            await self.C.offer("1", "给甲")
            await self.C.offer("2", "给乙")
            await asyncio.sleep(0.15)

        asyncio.run(main())
        targets = sorted(t for t, _ in self.got)
        self.assertEqual(targets, ["1", "2"])

    def test_window_cap(self):
        """一直发个不停，也必须在 window 内处理一次"""
        C = self.C
        C.window = 0.12
        C.debounce = 0.05

        async def main():
            for i in range(6):
                await C.offer("1", f"m{i}")
                await asyncio.sleep(0.03)
            await asyncio.sleep(0.1)

        asyncio.run(main())
        self.assertGreaterEqual(len(self.got), 1)
        self.assertLessEqual(len(self.got), 2, "窗口上限应强制 flush")

    def test_flush_all(self):
        async def main():
            await self.C.offer("1", "a")
            await self.C.offer("2", "b")
            await self.C.flush_all()

        asyncio.run(main())
        self.assertEqual(len(self.got), 2)
        self.assertEqual(self.C.stats()["pending"], 0)

    def test_handler_error_does_not_crash(self):
        from bot.chat.coalesce import Coalescer

        async def boom(target, items):
            raise RuntimeError("炸了")

        C = Coalescer(boom, debounce=0.03, window=0.1)

        async def main():
            await C.offer("1", "x")
            await asyncio.sleep(0.08)

        asyncio.run(main())      # 不应抛异常

    def test_stats_shape(self):
        s = self.C.stats()
        for key in ("pending", "batches", "merged", "flushes", "debounce", "window"):
            self.assertIn(key, s)


if __name__ == "__main__":
    unittest.main()
