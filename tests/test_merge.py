# ===================== 合并窗口测试（v17.2 U3） =====================

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


class TestMerger(unittest.TestCase):
    """窗口内合并、不同目标分开、聊天不合并、到量立刻发"""

    def setUp(self):
        from botv.egress.merge import Merger

        self.sent = []

        async def fake_send(target, text):
            self.sent.append((target, text))
            return True

        self.M = Merger(send=fake_send, window=0.1, max_items=3)

    def test_merges_within_window(self):
        async def main():
            await self.M.offer("1", "第一句", kind="schedule")
            await self.M.offer("1", "第二句", kind="schedule")
            await asyncio.sleep(0.3)

        asyncio.run(main())
        self.assertEqual(len(self.sent), 1, "两条应合成一次发送")
        self.assertIn("第一句", self.sent[0][1])
        self.assertIn("第二句", self.sent[0][1])
        self.assertEqual(self.M.stats()["merged"], 1)

    def test_chat_never_merged(self):
        async def main():
            ok = await self.M.offer("1", "聊天", kind="chat")
            return ok

        self.assertFalse(asyncio.run(main()), "聊天不该进合并窗口")
        self.assertEqual(self.M.stats()["pending"], 0)

    def test_image_never_merged(self):
        self.assertFalse(asyncio.run(self.M.offer("1", "", kind="schedule")),
                         "空文本不合并")

    def test_different_targets_separate(self):
        async def main():
            await self.M.offer("1", "给甲", kind="schedule")
            await self.M.offer("2", "给乙", kind="schedule")
            await asyncio.sleep(0.3)

        asyncio.run(main())
        self.assertEqual(len(self.sent), 2)
        targets = {t for t, _ in self.sent}
        self.assertEqual(targets, {"1", "2"})

    def test_max_items_flushes_early(self):
        async def main():
            for i in range(3):
                await self.M.offer("1", f"第{i}句", kind="schedule")
            # 不到窗口时间就该发出去
            await asyncio.sleep(0.02)

        asyncio.run(main())
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.M.stats()["pending"], 0)

    def test_single_item_sent_as_is(self):
        async def main():
            await self.M.offer("1", "只有一句", kind="schedule")
            await asyncio.sleep(0.3)

        asyncio.run(main())
        self.assertEqual(self.sent, [("1", "只有一句")])
        self.assertEqual(self.M.stats()["merged"], 0)

    def test_duplicate_lines_deduped(self):
        async def main():
            await self.M.offer("1", "一样的话", kind="schedule")
            await self.M.offer("1", "一样的话", kind="schedule")
            await asyncio.sleep(0.3)

        asyncio.run(main())
        self.assertEqual(self.sent[0][1], "一样的话")

    def test_flush_all(self):
        async def main():
            await self.M.offer("1", "a", kind="schedule")
            await self.M.offer("2", "b", kind="schedule")
            await self.M.flush_all()

        asyncio.run(main())
        self.assertEqual(len(self.sent), 2)
        self.assertEqual(self.M.stats()["pending"], 0)

    def test_stats_shape(self):
        s = self.M.stats()
        for key in ("pending", "merged", "flushed", "window", "targets"):
            self.assertIn(key, s)


if __name__ == "__main__":
    unittest.main()
