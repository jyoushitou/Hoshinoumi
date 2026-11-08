# ===================== 端口实现测试 =====================
# v5-R3/R4：验证三个适配器真的满足端口，并且行为与旧函数一致
# 运行：python -m unittest discover -s tests -v

import asyncio
import json
import sys
import types
import unittest

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass


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

    try:
        import jieba  # noqa: F401
    except ImportError:
        module("jieba", lcut=lambda s: list(s))

    try:
        import aiohttp  # noqa: F401
    except ImportError:
        aw = module("aiohttp")
        aw.web = module("aiohttp.web", middleware=lambda fn: fn,
                        json_response=lambda *a, **k: None,
                        Application=object, AppRunner=object, TCPSite=object)

    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        module("PIL", Image=None)


_stub_missing_deps()

from botv.ports import ChatModel, Transport  # noqa: E402
from botv.ports.models import ChatRequest, ChatReply  # noqa: E402
from botv.ports.transport import Target, Segment  # noqa: E402
from botv.ai import models as model_mod  # noqa: E402
from botv.ai.chain import FallbackChain  # noqa: E402
from botv.chat.transport import QqTransport  # noqa: E402


class FakeWS:
    def __init__(self):
        self.sent = []

    async def send(self, payload):
        self.sent.append(payload)


class TestChatModelAdapters(unittest.TestCase):

    def test_isinstance_protocol(self):
        self.assertIsInstance(model_mod.DeepSeekModel(), ChatModel)
        self.assertIsInstance(model_mod.DoubaoModel(), ChatModel)

    def test_deepseek_wraps_call(self):
        captured = {}

        async def fake(msgs, max_tokens=None, target_id=None):
            captured["n"] = len(msgs)
            return "哼"

        orig = model_mod.call_deepseek
        model_mod.call_deepseek = fake
        try:
            reply = asyncio.run(model_mod.DeepSeekModel().complete(
                ChatRequest(messages=[{"role": "user", "content": "hi"}])))
        finally:
            model_mod.call_deepseek = orig
        self.assertEqual(reply.text, "哼")
        self.assertEqual(reply.model, "deepseek")
        self.assertEqual(captured["n"], 1)

    def test_deepseek_empty_returns_none(self):
        async def fake(msgs, max_tokens=None, target_id=None):
            return None

        orig = model_mod.call_deepseek
        model_mod.call_deepseek = fake
        try:
            reply = asyncio.run(model_mod.DeepSeekModel().complete(
                ChatRequest(messages=[{"role": "user", "content": "hi"}])))
        finally:
            model_mod.call_deepseek = orig
        self.assertIsNone(reply)


class TestFallbackChain(unittest.TestCase):

    def _model(self, name, result):
        class M:
            supports_vision = False

            async def complete(self, req):
                return ChatReply(text=result, model=name) if result else None
        M.name = name
        return M()

    def test_first_wins(self):
        chain = FallbackChain([self._model("a", "A"), self._model("b", "B")])
        reply = asyncio.run(chain.complete(ChatRequest(messages=[])))
        self.assertEqual(reply.text, "A")

    def test_fallback_on_none(self):
        chain = FallbackChain([self._model("a", None), self._model("b", "B")])
        reply = asyncio.run(chain.complete(ChatRequest(messages=[])))
        self.assertEqual(reply.text, "B")

    def test_all_fail(self):
        chain = FallbackChain([self._model("a", None), self._model("b", None)])
        self.assertIsNone(asyncio.run(chain.complete(ChatRequest(messages=[]))))

    def test_exception_falls_through(self):
        class Boom:
            name = "boom"
            supports_vision = False

            async def complete(self, req):
                raise RuntimeError("炸了")

        chain = FallbackChain([Boom(), self._model("b", "B")])
        reply = asyncio.run(chain.complete(ChatRequest(messages=[])))
        self.assertEqual(reply.text, "B")


class TestTransport(unittest.TestCase):

    def test_isinstance_protocol(self):
        self.assertIsInstance(QqTransport(FakeWS()), Transport)

    def test_send_private(self):
        ws = FakeWS()
        t = QqTransport(ws)
        asyncio.run(t.send(Target(kind="private", id=123), [Segment(type="text", data={"text": "hi"})]))
        payload = json.loads(ws.sent[0])
        self.assertEqual(payload["action"], "send_private_msg")
        self.assertEqual(payload["params"]["user_id"], 123)
        self.assertEqual(payload["params"]["message"][0]["data"]["text"], "hi")

    def test_send_group(self):
        ws = FakeWS()
        t = QqTransport(ws)
        asyncio.run(t.send(Target(kind="group", id=456), [Segment(type="image", data={"file": "/a.jpg"})]))
        payload = json.loads(ws.sent[0])
        self.assertEqual(payload["action"], "send_group_msg")
        self.assertEqual(payload["params"]["group_id"], 456)

    def test_poke(self):
        ws = FakeWS()
        t = QqTransport(ws)
        asyncio.run(t.poke(Target(kind="group", id=456), 789))
        payload = json.loads(ws.sent[0])
        self.assertEqual(payload["action"], "send_poke")
        self.assertEqual(payload["params"]["user_id"], 789)
        self.assertEqual(payload["params"]["group_id"], 456)


if __name__ == "__main__":
    unittest.main()
