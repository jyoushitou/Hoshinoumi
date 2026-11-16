# ===================== v27.6 心跳读取最新连接 =====================
import asyncio
import unittest
from unittest import mock


class _WS:
    def __init__(self):
        self.closed = False
        self.pings = 0

    async def ping(self):
        self.pings += 1

    async def close(self):
        self.closed = True


class TestHeartbeat(unittest.TestCase):
    def _run_briefly(self, ref, ws):
        async def run():
            with mock.patch("bot.heartbeat.HEARTBEAT_INTERVAL", 0.01):
                task = asyncio.create_task(
                    __import__("bot.heartbeat", fromlist=["heartbeat_monitor"]).heartbeat_monitor("QQ", ref))
                await asyncio.sleep(0.05)
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        asyncio.run(run())

    def test_callable_sees_none_then_connection(self):
        from bot import heartbeat

        ws = _WS()
        state = {"ws": None}
        original = heartbeat.HEARTBEAT_INTERVAL
        try:
            async def run():
                heartbeat.HEARTBEAT_INTERVAL = 0.01
                task = asyncio.create_task(heartbeat.heartbeat_monitor("QQ", lambda: state["ws"]))
                await asyncio.sleep(0.02)
                state["ws"] = ws
                await asyncio.sleep(0.04)
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            asyncio.run(run())
        finally:
            heartbeat.HEARTBEAT_INTERVAL = original
        self.assertGreaterEqual(ws.pings, 1)

    def test_object_ref_still_compatible(self):
        ws = _WS()
        self._run_briefly(ws, ws)
        self.assertGreaterEqual(ws.pings, 1)


if __name__ == "__main__":
    unittest.main()
