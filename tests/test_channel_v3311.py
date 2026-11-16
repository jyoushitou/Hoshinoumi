# ===================== v33.1.1.1 通道契约 + QQ native =====================
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

from bot.channels.qq import QQChannel
from bot.ports.channel import Channel, InboundMessage


class TestChannelV3311(unittest.TestCase):
    def test_protocol(self):
        self.assertIsInstance(QQChannel(), Channel)

    def test_start_stop(self):
        c = QQChannel()
        self.assertFalse(c.started)
        asyncio.run(c.start())
        self.assertTrue(c.started)
        asyncio.run(c.stop())
        self.assertFalse(c.started)

    def test_send_private(self):
        c = QQChannel()
        asyncio.run(c.start())
        with mock.patch("bot.chat.send.send_private_msg", new=mock.AsyncMock()) as send:
            ok = asyncio.run(c.send("1", "hi"))
        self.assertTrue(ok)
        self.assertTrue(send.called)

    def test_inbound(self):
        m = InboundMessage("qq", "1", "1", "hi")
        self.assertEqual(m.text, "hi")


if __name__ == "__main__":
    unittest.main()
