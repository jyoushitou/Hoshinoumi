# ===================== v35.2.1 Endpoint + DeliveryHub =====================
import asyncio
import json
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path


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

    def json_response(data, status=200, dumps=None):
        return _Resp(json.dumps(data, ensure_ascii=False), status)

    web.json_response = json_response
    web.middleware = lambda fn: fn
    web.Application = object
    aio = types.ModuleType("aiohttp")
    aio.web = web
    sys.modules["aiohttp"] = aio
    sys.modules["aiohttp.web"] = web


_stub_aiohttp()

try:
    import jieba  # noqa: F401
except ImportError:
    m = types.ModuleType("jieba")
    m.lcut = lambda text: list(text)
    sys.modules["jieba"] = m

from bot.infra import conn, schema  # noqa: E402
from bot.infra import repo_delivery  # noqa: E402
from bot.delivery import hub  # noqa: E402
from scripts import migrate_v33, migrate_v34, migrate_v35  # noqa: E402


class FakeRequest:
    def __init__(self, name="", body=None, headers=None, match=None, query=None):
        self._body = body or {}
        self.headers = headers or {}
        self.match_info = match or {}
        self.query = query or {}
        if name:
            self.match_info["name"] = name

    async def json(self):
        return self._body


def _body(resp):
    return json.loads(resp.text)


class TestDelivery(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        conn.configure(backend="sqlite", sqlite_path=str(Path(self.tmp) / "d.db"))
        self.c = conn.get_cursor()
        schema.ensure_tables(self.c)
        migrate_v33.apply(self.c)
        migrate_v34.apply(self.c)
        migrate_v35.apply(self.c)
        self.c.close()

    def tearDown(self):
        conn.configure(backend=None, sqlite_path=None, mysql_config=None)

    def test_schema_tables(self):
        c = conn.get_cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        names = {r["name"] for r in c.fetchall()}
        c.close()
        self.assertIn("client_endpoints", names)
        self.assertIn("delivery_outbox", names)

    def test_register_fanout_pull_ack(self):
        row, token = hub.register("__owner__", "phone", "android")
        self.assertIn("nao_ep_", token)
        n = hub.fanout_text("__owner__", "123", "hi", "private", "m1")
        self.assertEqual(n, 1)
        # 幂等：同 endpoint/message 不重复
        self.assertEqual(hub.fanout_text("__owner__", "123", "hi", "private", "m1"), 0)
        rows = repo_delivery.pull("__owner__", row["id"])
        self.assertEqual(len(rows), 1)
        self.assertIn("hi", rows[0]["payload_json"])
        self.assertTrue(repo_delivery.ack("__owner__", row["id"], "m1"))
        self.assertEqual(repo_delivery.pull("__owner__", row["id"]), [])

    def test_disable_endpoint(self):
        row, _ = hub.register("__owner__", "pc", "desktop")
        self.assertTrue(repo_delivery.disable_endpoint("__owner__", row["id"]))
        self.assertEqual(repo_delivery.enabled_endpoints("__owner__"), [])

    def test_pull_requires_token(self):
        from bot.server import routes_endpoints
        row, token = hub.register("__owner__", "phone2", "android")
        req = FakeRequest(headers={"X-Endpoint-Token": "wrong"},
                          match={"id": str(row["id"])})
        resp = asyncio.run(routes_endpoints.handle_messages(req))
        self.assertEqual(resp.status, 403)
        req2 = FakeRequest(headers={"X-Endpoint-Token": token},
                           match={"id": str(row["id"])})
        resp2 = asyncio.run(routes_endpoints.handle_messages(req2))
        self.assertEqual(resp2.status, 200)

    def test_routes_wired(self):
        import bot.server.http_api as api
        with open(api.__file__, encoding="utf-8") as f:
            src = f.read()
        self.assertIn("/api/endpoints", src)
        self.assertIn("/api/endpoints/{id}/messages", src)


if __name__ == "__main__":
    unittest.main()
