# ===================== v35.2.25.0 关系 API =====================
import asyncio
import json
import sys
import types
import unittest
from unittest.mock import patch


def _stub_aiohttp():
    try:
        import aiohttp  # noqa: F401
        return
    except ImportError:
        pass
    web = types.ModuleType("aiohttp.web")
    web.json_response = lambda data, status=200, dumps=None: type("R", (), {
        "text": (dumps or (lambda x: json.dumps(x, ensure_ascii=False)))(data), "status": status})()
    web.Application = object
    web.middleware = lambda fn: fn
    web.RouteTableDef = lambda: []
    aio = types.ModuleType("aiohttp")
    aio.web = web
    sys.modules["aiohttp"] = aio
    sys.modules["aiohttp.web"] = web


_stub_aiohttp()
from bot.server import routes_relation  # noqa: E402
from bot.infra import tenant  # noqa: E402


class _Req:
    def __init__(self, query=None, headers=None):
        self.query = query or {}
        self.headers = headers or {}


class RelationTests(unittest.TestCase):
    def test_relation_shape(self):
        with patch.object(routes_relation.relation, "get", return_value=0.62), \
             patch.object(routes_relation.relation, "recent_events", return_value=[{"delta": 0.02, "reason": "聊天"}]):
            resp = asyncio.run(routes_relation.handle_relation(_Req()))
        data = json.loads(resp.text)
        self.assertTrue(data["ok"])
        self.assertEqual(data["affinity"], 0.62)
        self.assertEqual(data["tier"], "熟")
        self.assertEqual(len(data["events"]), 1)

    def test_non_owner_forced_to_self(self):
        req = _Req({"target_id": "822891053"}, {"X-User-Id": "10001"})
        with patch.object(routes_relation.relation, "get", return_value=0.18), \
             patch.object(routes_relation.relation, "recent_events", return_value=[]):
            resp = asyncio.run(routes_relation.handle_relation(req))
        data = json.loads(resp.text)
        self.assertFalse(data["can_view_all"])
        self.assertEqual(data["target_id"], "10001")

    def test_owner_can_view_other(self):
        req = _Req({"target_id": "10001"}, {"X-User-Id": tenant.owner_id()})
        with patch.object(routes_relation.relation, "get", return_value=0.2), \
             patch.object(routes_relation.relation, "recent_events", return_value=[]):
            resp = asyncio.run(routes_relation.handle_relation(req))
        data = json.loads(resp.text)
        self.assertTrue(data["can_view_all"])
        self.assertEqual(data["target_id"], "10001")

    def test_relation_failure_is_json(self):
        with patch.object(routes_relation.relation, "get", side_effect=RuntimeError("db down")):
            resp = asyncio.run(routes_relation.handle_relation(_Req()))
        data = json.loads(resp.text)
        self.assertFalse(data["ok"])
        self.assertEqual(resp.status, 500)


if __name__ == "__main__":
    unittest.main()
