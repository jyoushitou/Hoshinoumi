# ===================== v18.6 引用上下文 =====================
# 覆盖：缓存命中 / get_msg 兜底 / 超时降级 / 关键词不污染 / 环形缓存

import asyncio
import re
import sys
import types
import unittest
from unittest.mock import patch


def _stub_missing_deps():
    """缺依赖就打桩（必须在导入 bot 之前）"""
    try:
        import jieba  # noqa: F401
    except ImportError:
        m = types.ModuleType("jieba")
        m.lcut = lambda s: [t for t in re.split(r"[\s，。！？、：；【】]+", s or "") if t]
        sys.modules["jieba"] = m
    try:
        import pymysql  # noqa: F401
    except ImportError:
        sys.modules["pymysql"] = types.ModuleType("pymysql")


_stub_missing_deps()

from bot.chat import cache  # noqa: E402
from bot.chat.inbound import parse_message_content  # noqa: E402
from bot.memory.text import extract_keywords  # noqa: E402


def _raw(mid, text="这个"):
    return [{"type": "reply", "data": {"id": mid}},
            {"type": "text", "data": {"text": text}}]


class TestQuoteContext(unittest.TestCase):
    def setUp(self):
        cache.clear()

    def test_cache_hit_no_get_msg(self):
        cache.remember(123, "友利奈绪", "之前不是还慌得不行。")
        text, _ = asyncio.run(parse_message_content(_raw(123), "1", None))
        self.assertIn("【引用 友利奈绪】原话：之前不是还慌得不行。", text)
        self.assertIn("这个", text)
        self.assertNotIn("[引用]", text)

    def test_miss_fetches_get_msg(self):
        calls = []

        async def fake(action, params, ws, label, **kwargs):
            calls.append((action, params.get("message_id"), kwargs.get("timeout")))
            return {"data": {"raw_message": "原话在这里",
                             "sender": {"nickname": "友利奈绪"}}}

        with patch("bot.chat.send.request_action", fake):
            text, _ = asyncio.run(parse_message_content(_raw(999), "1", object()))
        self.assertIn("【引用 友利奈绪】原话：原话在这里", text)
        self.assertEqual(calls, [("get_msg", 999, 2)])
        self.assertIsNotNone(cache.get(999))

    def test_miss_timeout_degrades(self):
        async def boom(*args, **kwargs):
            raise asyncio.TimeoutError()

        with patch("bot.chat.send.request_action", boom):
            text, _ = asyncio.run(parse_message_content(_raw(1000), "1", object()))
        self.assertIn("（他引用了一条较早的消息，你看不到，别装懂）", text)
        self.assertNotIn("[引用]", text)

    def test_quote_metrics(self):
        from bot.core import metrics
        before = metrics.snapshot()[0].get("quote_hit", 0)
        cache.remember(456, "友利奈绪", "原话")
        asyncio.run(parse_message_content(_raw(456), "1", None))
        after = metrics.snapshot()[0].get("quote_hit", 0)
        self.assertEqual(after, before + 1)

    def test_quote_label_not_in_keywords(self):
        cache.remember(321, "友利奈绪", "之前不是还慌得不行。")
        text, _ = asyncio.run(parse_message_content(_raw(321), "1", None))
        kws = extract_keywords(text)
        self.assertNotIn("引用", kws)
        self.assertNotIn("原话", kws)

    def test_ring_keeps_last_200(self):
        for i in range(205):
            cache.remember(i, "某人", f"第{i}条")
        self.assertEqual(cache.size(), 200)
        self.assertIsNone(cache.get(0))
        self.assertIsNotNone(cache.get(204))


if __name__ == "__main__":
    unittest.main()
