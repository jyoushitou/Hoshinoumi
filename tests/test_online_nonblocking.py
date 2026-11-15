# ===================== v27.3.1 上线配图非阻塞 =====================
import asyncio
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

try:
    import jieba  # noqa: F401
except ImportError:
    m = types.ModuleType("jieba")
    m.lcut = lambda s: list(s)
    sys.modules["jieba"] = m


class TestOnlineImageNonblocking(unittest.TestCase):
    def test_image_is_scheduled_not_awaited_before_recv(self):
        src = Path("bot/chat/handler.py").read_text(encoding="utf-8")
        self.assertIn("_send_online_notice(ws)", src)
        self.assertIn("_bg_ws.get(_t) is ws", src)
        self.assertIn("_online_ws.get(_t) is ws", src)

    def test_image_error_is_swallowed(self):
        import bot.chat.handler as h

        async def run():
            with mock.patch.object(h, "fetch_and_save_acg_image",
                                   side_effect=RuntimeError("network")):
                await h._send_online_notice(types.SimpleNamespace(closed=False))
        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
