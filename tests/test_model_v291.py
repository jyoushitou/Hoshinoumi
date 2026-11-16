# ===================== v29.1 DeepSeek native provider =====================
import asyncio
import sys
import types
import unittest
from unittest import mock

try:
    import jieba  # noqa: F401
except ImportError:
    m = types.ModuleType("jieba")
    m.lcut = lambda s: list(s)
    sys.modules["jieba"] = m

from bot.ai.providers import DeepSeekProvider
from bot.ports.models import ModelProvider, ModelRequest


class TestDeepSeekProvider(unittest.TestCase):
    def test_protocol_and_capabilities(self):
        p = DeepSeekProvider()
        self.assertIsInstance(p, ModelProvider)
        self.assertEqual(p.capabilities(), {"text"})

    def test_wraps_call(self):
        async def fake(msgs, max_tokens=None, target_id=None):
            return "ok"
        with mock.patch("bot.ai.providers.call_deepseek", side_effect=fake):
            reply = asyncio.run(DeepSeekProvider().complete(
                ModelRequest(messages=[{"role": "user", "content": "hi"}],
                             max_tokens=10, target_id="1")))
        self.assertEqual(reply.text, "ok")
        self.assertEqual(reply.model, "deepseek")
        self.assertFalse(reply.fallback)

    def test_empty_returns_none(self):
        async def fake(msgs, max_tokens=None, target_id=None):
            return None
        with mock.patch("bot.ai.providers.call_deepseek", side_effect=fake):
            self.assertIsNone(asyncio.run(DeepSeekProvider().complete(
                ModelRequest(messages=[]))))


if __name__ == "__main__":
    unittest.main()
