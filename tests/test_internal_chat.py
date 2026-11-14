# ===================== v21.2 网关对话入库 =====================
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

    for name in ("jieba", "PIL"):
        try:
            __import__(name)
        except ImportError:
            module(name, lcut=lambda s: list(s), Image=None)

    try:
        import aiohttp  # noqa: F401
    except ImportError:
        web = module("aiohttp.web")

        class _Resp:
            def __init__(self, body, status=200, content_type=None):
                self.text = body
                self.body = body.encode("utf-8") if isinstance(body, str) else body
                self.status = status

        def json_response(data, status=200, dumps=None):
            return _Resp(json.dumps(data, ensure_ascii=False), status)

        web.json_response = json_response
        web.Response = _Resp
        web.middleware = lambda fn: fn
        web.Application = object
        web.RouteTableDef = lambda: []

        aio = module("aiohttp")
        aio.web = web


_stub_missing_deps()


class FakeRequest:
    def __init__(self, body, headers=None, query=None):
        self._body = body
        self.headers = headers or {}
        self.query = query or {}

    async def json(self):
        return self._body


def _body(resp):
    try:
        return json.loads(resp.text)
    except Exception:
        return json.loads(resp.body.decode("utf-8"))


class TestInternalChatHistory(unittest.TestCase):
    def setUp(self):
        from bot.server import http_api

        self.H = http_api
        self.appended = []
        self.orig_get = None
        self.orig_append = None

    def tearDown(self):
        if self.orig_get is not None:
            import bot.ai.client as client
            client.get_character_reply = self.orig_get
        if self.orig_append is not None:
            import bot.infra.repo_conversation as repo
            repo.append = self.orig_append

    def _patch(self, reply="在。", fail=False):
        import bot.ai.client as client
        import bot.infra.repo_conversation as repo

        self.orig_get = client.get_character_reply
        self.orig_append = repo.append

        async def fake_reply(message, target_id, keywords=None):
            if fail:
                raise RuntimeError("model down")
            return reply

        def fake_append(**kwargs):
            self.appended.append(kwargs)
            return True

        client.get_character_reply = fake_reply
        repo.append = fake_append

    def test_success_writes_user_and_assistant(self):
        self._patch()
        req = FakeRequest(
            {"message": "网关测试", "target_id": "__owner__", "client_message_id": "c1"},
            headers={"X-Owner-Id": "owner"},
        )
        resp = asyncio.run(self.H.handle_internal_chat(req))
        body = _body(resp)
        self.assertTrue(body["success"])
        self.assertEqual(len(self.appended), 2)
        self.assertEqual(self.appended[0]["role"], "user")
        self.assertEqual(self.appended[0]["channel"], "gateway")
        self.assertEqual(self.appended[0]["user_id"], "__owner__")
        self.assertEqual(self.appended[0]["target_id"], "__owner__")
        self.assertEqual(self.appended[1]["role"], "assistant")
        self.assertIn("gw-user:c1", self.appended[0]["message_id"])
        self.assertIn("gw-assistant:c1", self.appended[1]["message_id"])

    def test_failure_writes_nothing(self):
        self._patch(fail=True)
        req = FakeRequest(
            {"message": "会失败", "target_id": "__owner__", "client_message_id": "c2"},
            headers={"X-Owner-Id": "owner"},
        )
        resp = asyncio.run(self.H.handle_internal_chat(req))
        self.assertEqual(resp.status, 500)
        self.assertEqual(self.appended, [])

    def test_missing_target_writes_nothing(self):
        self._patch()
        req = FakeRequest({"message": "hi", "client_message_id": "c3"})
        resp = asyncio.run(self.H.handle_internal_chat(req))
        self.assertEqual(resp.status, 400)
        self.assertEqual(self.appended, [])


if __name__ == "__main__":
    unittest.main()

