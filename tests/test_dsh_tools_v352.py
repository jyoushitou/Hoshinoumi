# ===================== v35.2.0.0 DSH 只读工具桥 =====================
import asyncio
import json
import sys
import types
import unittest


def _stub_aiohttp():
    try:
        import aiohttp  # noqa: F401
        return
    except ImportError:
        pass

    web = types.ModuleType("aiohttp.web")

    class _Resp:
        def __init__(self, body, status=200, content_type=None):
            self.text = body
            self.body = body.encode("utf-8") if isinstance(body, str) else body
            self.status = status
            self.content_type = content_type

    def json_response(data, status=200, dumps=None):
        return _Resp(json.dumps(data, ensure_ascii=False), status)

    def middleware(fn):
        return fn

    web.json_response = json_response
    web.Response = _Resp
    web.middleware = middleware
    web.Application = object
    web.RouteTableDef = lambda: []
    aio = types.ModuleType("aiohttp")
    aio.web = web
    sys.modules["aiohttp"] = aio
    sys.modules["aiohttp.web"] = web


_stub_aiohttp()

for name, attrs in (("jieba", {"lcut": lambda s: list(s)}),):
    if name not in sys.modules:
        try:
            __import__(name)
        except ImportError:
            m = types.ModuleType(name)
            for k, v in attrs.items():
                setattr(m, k, v)
            sys.modules[name] = m
try:
    import pymysql  # noqa: F401
except ImportError:
    m = types.ModuleType("pymysql")
    m.connect = lambda **kw: None
    sys.modules["pymysql"] = m
    c = types.ModuleType("pymysql.cursors")
    c.DictCursor = object
    sys.modules["pymysql.cursors"] = c
    m.cursors = c

from bot.server import routes_tools  # noqa: E402


class FakeRequest:
    def __init__(self, name="", body=None):
        self.match_info = {"name": name}
        self._body = body or {}
        self.query = {}

    async def json(self):
        return self._body


def _body(resp):
    return json.loads(resp.text)


class TestDshTools(unittest.TestCase):
    def test_list_only_readonly(self):
        body = _body(asyncio.run(routes_tools.handle_list(FakeRequest())))
        self.assertTrue(body["ok"])
        self.assertTrue(body["read_only"])
        names = [t["name"] for t in body["tools"]]
        self.assertEqual(names, ["recall", "search_images"])
        self.assertNotIn("remember", names)
        self.assertNotIn("agenda_add", names)

    def test_write_tool_blocked(self):
        resp = asyncio.run(routes_tools.handle_call(
            FakeRequest("remember", {"arg": "x"})))
        self.assertEqual(resp.status, 403)
        self.assertEqual(_body(resp)["error"], "tool_not_allowed")

    def test_missing_arg(self):
        resp = asyncio.run(routes_tools.handle_call(
            FakeRequest("recall", {})))
        self.assertEqual(resp.status, 400)
        self.assertEqual(_body(resp)["error"], "missing_arg")

    def test_call_recall(self):
        old = routes_tools.run_tool

        async def fake(name, arg, tid):
            return f"{name}:{arg}:{tid}"

        routes_tools.run_tool = fake
        try:
            resp = asyncio.run(routes_tools.handle_call(
                FakeRequest("recall", {"arg": "昨天"})))
            body = _body(resp)
            self.assertEqual(resp.status, 200)
            self.assertTrue(body["ok"])
            self.assertEqual(body["tool"], "recall")
            self.assertIn("昨天", body["result"])
        finally:
            routes_tools.run_tool = old

    def test_manifest(self):
        from pathlib import Path
        m = json.loads(Path("integrations/dsh/manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(m["name"], "hoshinoumi-dsh")
        self.assertTrue(m["read_only"])
        self.assertEqual({t["name"] for t in m["tools"]},
                         {"recall", "search_images"})

    def test_routes_wired(self):
        import bot.server.http_api as api
        with open(api.__file__, encoding="utf-8") as f:
            src = f.read()
        self.assertIn("/api/tools", src)
        self.assertIn("/api/tools/{name}/call", src)


if __name__ == "__main__":
    unittest.main()
