# ===================== 出站口测试（v17.2.0） =====================

import asyncio
import json
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


class FakeWS:
    def __init__(self, delay=0.0, broken=False):
        self.sent = []
        self.delay = delay
        self.broken = broken
        self.closed = False
        self.inflight = 0
        self.max_inflight = 0

    async def send(self, payload):
        self.inflight += 1
        self.max_inflight = max(self.max_inflight, self.inflight)
        try:
            if self.delay:
                await asyncio.sleep(self.delay)
            if self.broken:
                raise RuntimeError("断了")
            self.sent.append(payload)
        finally:
            self.inflight -= 1


def _out(ws, lock=None):
    from botv.egress.outbound import Outbound

    return Outbound(ws=ws, lock=lock)


class TestOutbound(unittest.TestCase):
    """发送、锁、断线入队、echo 等待、计数"""

    def setUp(self):
        from botv.core import state as cfg

        cfg.pending_outbox.clear()
        cfg.pending_echo.clear()

    def tearDown(self):
        from botv.core import state as cfg

        cfg.pending_outbox.clear()
        cfg.pending_echo.clear()

    def test_send_ok(self):
        ws = FakeWS()
        out = _out(ws)
        ok = asyncio.run(out.send("send_private_msg", {"user_id": 1}, label="测试"))
        self.assertTrue(ok)
        self.assertEqual(len(ws.sent), 1)
        payload = json.loads(ws.sent[0])
        self.assertEqual(payload["action"], "send_private_msg")

    def test_lock_serializes(self):
        """并发 10 条，任意时刻只有 1 条在发"""
        ws = FakeWS(delay=0.01)
        out = _out(ws)

        async def main():
            await asyncio.gather(*[
                out.send("x", {"i": i}, label=f"m{i}") for i in range(10)
            ])

        asyncio.run(main())
        self.assertEqual(len(ws.sent), 10)
        self.assertEqual(ws.max_inflight, 1, "全局锁没生效，出现并发发送")

    def test_disconnected_enqueues(self):
        out = _out(None)
        ok = asyncio.run(out.send("a", {}, label="断线"))
        self.assertFalse(ok)
        from botv.core import state as cfg

        self.assertEqual(len(cfg.pending_outbox), 1)
        self.assertEqual(out.stats()["queued"], 1)

    def test_send_error_enqueues(self):
        ws = FakeWS(broken=True)
        out = _out(ws)
        ok = asyncio.run(out.send("a", {}, label="失败"))
        self.assertFalse(ok)
        from botv.core import state as cfg

        self.assertEqual(len(cfg.pending_outbox), 1)
        self.assertEqual(out.stats()["failed"], 1)

    def test_want_response_gets_data(self):
        ws = FakeWS()
        out = _out(ws)

        async def main():
            task = asyncio.create_task(
                out.send("get_msg", {"message_id": 1}, want_response=True, timeout=1))
            await asyncio.sleep(0.02)
            echo = list(__import__("botv.core.state", fromlist=["cfg"]).pending_echo)[0]
            __import__("botv.core.state", fromlist=["cfg"]).pending_echo[echo].set_result(
                {"message_id": 42})
            return await task

        data = asyncio.run(main())
        self.assertEqual(data, {"message_id": 42})

    def test_want_response_timeout(self):
        ws = FakeWS()
        out = _out(ws)
        data = asyncio.run(out.send("get_msg", {}, want_response=True, timeout=0.05))
        self.assertIsNone(data)
        self.assertEqual(out.stats()["echo_timeout"], 1)

    def test_flush(self):
        from botv.core import state as cfg

        cfg.pending_outbox.append('{"action":"a","params":{}}')
        cfg.pending_outbox.append('{"action":"b","params":{}}')
        ws = FakeWS()
        out = _out(ws)
        n = asyncio.run(out.flush())
        self.assertEqual(n, 2)
        self.assertEqual(len(cfg.pending_outbox), 0)
        self.assertEqual(len(ws.sent), 2)

    def test_flush_noop_when_offline(self):
        from botv.core import state as cfg

        cfg.pending_outbox.append("x")
        out = _out(None)
        self.assertEqual(asyncio.run(out.flush()), 0)

    def test_stats_and_describe(self):
        out = _out(FakeWS())
        asyncio.run(out.send("a", {}, kind="chat"))
        s = out.stats()
        for key in ("alive", "sent", "failed", "queued", "echo_timeout", "pending"):
            self.assertIn(key, s)
        self.assertIn("出站", out.describe())
        self.assertEqual(s["by_kind"]["chat"]["sent"], 1)

    def test_bind_swaps_ws(self):
        out = _out(None)
        ws = FakeWS()
        out.bind(ws)
        self.assertTrue(out.alive())
        asyncio.run(out.send("a", {}))
        self.assertEqual(len(ws.sent), 1)


if __name__ == "__main__":
    unittest.main()
