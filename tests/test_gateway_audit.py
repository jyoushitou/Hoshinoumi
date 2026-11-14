# ===================== v22.0 网关审计 =====================
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
            def __init__(self, body, status=200):
                self.text = body
                self.status = status

        web.json_response = lambda data, status=200, dumps=None: _Resp(
            (dumps or (lambda x: json.dumps(x, ensure_ascii=False)))(data), status)
        web.Response = _Resp
        web.middleware = lambda fn: fn
        web.Application = object
        web.RouteTableDef = lambda: []
        aio = module("aiohttp")
        aio.web = web


_stub_missing_deps()


class _Req:
    def __init__(self, body):
        self._body = body
        self.headers = {}
        self.query = {}

    async def json(self):
        return self._body


class _Cur:
    def __init__(self):
        self.sql = None
        self.params = None
        self.connection = types.SimpleNamespace(commit=lambda: None)

    def execute(self, sql, params=None):
        self.sql = sql
        self.params = params


class TestGatewayAudit(unittest.TestCase):
    def test_audit_inserts_metadata_only(self):
        from bot.server import http_api
        from bot.infra import conn

        cur = _Cur()
        orig = conn.get_cursor
        conn.get_cursor = lambda: cur
        try:
            body = {"owner": "owner", "path": "/api/state", "status": 200,
                    "cost_ms": 12, "ip": "127.0.0.1", "request_id": "r1",
                    "token": "should-not-store", "body": "secret"}
            resp = asyncio.run(http_api.handle_internal_audit(_Req(body)))
        finally:
            conn.get_cursor = orig
        self.assertEqual(resp.status, 200)
        self.assertIn("gateway_log", cur.sql)
        self.assertNotIn("should-not-store", str(cur.params))
        self.assertNotIn("secret", str(cur.params))
        self.assertEqual(cur.params[0], "owner")
        self.assertEqual(cur.params[1], "/api/state")
        self.assertEqual(cur.params[2], 200)


if __name__ == "__main__":
    unittest.main()

