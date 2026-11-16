# ===================== v29.2 Doubao native provider =====================
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

from bot.ai.providers import DoubaoProvider
from bot.core.types import Fallback
from bot.ports.models import ModelProvider, ModelRequest


class TestDoubaoProvider(unittest.TestCase):
    def test_protocol_and_capabilities(self):
        p = DoubaoProvider()
        self.assertIsInstance(p, ModelProvider)
        self.assertEqual(p.capabilities(), {"text"})

    def test_fallback_flag(self):
        async def fake(msgs, max_tokens=None, target_id=None):
            return Fallback("哼")
        with mock.patch("bot.ai.providers.call_doubao", side_effect=fake):
            reply = asyncio.run(DoubaoProvider().complete(
                ModelRequest(messages=[{"role": "user", "content": "hi"}])))
        self.assertTrue(reply.fallback)
        self.assertEqual(reply.text, "哼")

    def test_empty_returns_none(self):
        async def fake(msgs, max_tokens=None, target_id=None):
            return None
        with mock.patch("bot.ai.providers.call_doubao", side_effect=fake):
            self.assertIsNone(asyncio.run(DoubaoProvider().complete(
                ModelRequest(messages=[]))))


if __name__ == "__main__":
    unittest.main()
