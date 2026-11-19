# ===================== v35.2.18.0 人设卡只读 API =====================
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
            self.status = status

    def json_response(data, status=200, dumps=None):
        return _Resp((dumps or (lambda x: json.dumps(x, ensure_ascii=False)))(data), status)

    web.json_response = json_response
    web.Application = object
    web.middleware = lambda fn: fn
    web.RouteTableDef = lambda: []
    aio = types.ModuleType("aiohttp")
    aio.web = web
    sys.modules["aiohttp"] = aio
    sys.modules["aiohttp.web"] = web


_stub_aiohttp()

from bot.server import routes_persona  # noqa: E402
from bot.server.routes_persona import cards, handle_persona  # noqa: E402


class _PostReq:
    def __init__(self, body, query=None):
        self._body = body
        self.query = query or {}

    async def json(self):
        return self._body


class _Req:
    def __init__(self, query=None):
        self.query = query or {}


class PersonaApiTests(unittest.TestCase):
    def test_cards_include_nao_and_files(self):
        rows = cards()
        self.assertTrue(rows)
        nao = next((x for x in rows if x["name"] == "nao"), None)
        self.assertIsNotNone(nao)
        self.assertIn("prompt", nao["files"])
        self.assertTrue(nao["files"]["prompt"])
        self.assertNotIn("prompt", nao)  # 默认不返回全文

    def test_list_shape(self):
        resp = asyncio.run(handle_persona(_Req()))
        data = json.loads(resp.text)
        self.assertTrue(data["ok"])
        self.assertEqual(data["count"], len(data["data"]))
        self.assertIn("active", data)

    def test_detail_and_traversal(self):
        resp = asyncio.run(handle_persona(_Req({"name": "nao"})))
        data = json.loads(resp.text)
        self.assertTrue(data["ok"])
        self.assertEqual(data["data"]["name"], "nao")
        bad = asyncio.run(handle_persona(_Req({"name": "../nao"})))
        self.assertEqual(bad.status, 404)

    def test_import_export_with_temp_card(self):
        import tempfile
        from pathlib import Path as _Path
        with tempfile.TemporaryDirectory() as td:
            old = routes_persona.CARD_ROOT
            routes_persona.CARD_ROOT = _Path(td)
            try:
                body = {"name": "test_card", "prompt": "你是测试角色", "state": {"mood": 0.2}}
                resp = asyncio.run(routes_persona.handle_import(_PostReq(body)))
                data = json.loads(resp.text)
                self.assertTrue(data["ok"])
                self.assertTrue((_Path(td) / "test_card" / "prompt.txt").is_file())
                # 不覆盖同名
                resp2 = asyncio.run(routes_persona.handle_import(_PostReq(body)))
                self.assertEqual(resp2.status, 409)
                resp3 = asyncio.run(routes_persona.handle_export(_Req({"name": "test_card"})))
                exported = json.loads(resp3.text)
                self.assertEqual(exported["data"]["name"], "test_card")
                self.assertIn("prompt", exported["data"])
            finally:
                routes_persona.CARD_ROOT = old

    def test_full_only_on_request(self):
        resp = asyncio.run(handle_persona(_Req({"name": "nao", "full": "1"})))
        data = json.loads(resp.text)
        self.assertTrue(data["ok"])
        self.assertIn("prompt", data["data"])
        self.assertTrue(data["data"]["prompt"])


if __name__ == "__main__":
    unittest.main()
