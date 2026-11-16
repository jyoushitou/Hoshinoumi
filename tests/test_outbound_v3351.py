# ===================== v33.5.1.1 Transport 契约 + WS native =====================
import asyncio
import sys
import types
import unittest
from unittest import mock

try:
    import jieba  # noqa: F401
except ImportError:
    m=types.ModuleType('jieba'); m.lcut=lambda s:list(s); sys.modules['jieba']=m

import bot.chat.send  # noqa: F401
from bot.egress.native import WebSocketTransport
from bot.ports.transport import Segment, Target, Transport


class TestOutboundV3351(unittest.TestCase):
    def test_protocol(self):
        self.assertIsInstance(WebSocketTransport(), Transport)

    def test_send_private(self):
        t = WebSocketTransport()
        with mock.patch("bot.chat.send.send_private_msg", new=mock.AsyncMock()) as s:
            asyncio.run(t.send(Target("private", "1"), [Segment("text", {"text": "x"})]))
        self.assertTrue(s.called)


if __name__ == "__main__": unittest.main()
