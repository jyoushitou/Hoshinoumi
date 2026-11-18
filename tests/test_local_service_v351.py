# ===================== v35.1.0.0 本机服务健康检查 =====================
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

# http_api 会间接 import jieba / pymysql；测试环境没有就最小 stub
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

from bot.server import routes_meta  # noqa: E402


class FakeRequest:
    pass


class FakeCursor:
    def __init__(self, schema="33"):
        self.schema = schema
        self.last = ""

    def execute(self, sql):
        self.last = sql

    def fetchone(self):
        if "bot_meta" in self.last:
            return {"v": self.schema} if self.schema is not None else None
        return None


def _body(resp):
    return json.loads(resp.text)


class TestLocalServiceHealth(unittest.TestCase):
    def test_healthz_ok(self):
        resp = asyncio.run(routes_meta.handle_healthz(FakeRequest()))
        body = _body(resp)
        self.assertEqual(resp.status, 200)
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["service"], "local")

    def test_readyz_ok_schema_33(self):
        import bot.infra.conn as conn
        old = conn.get_cursor
        conn.get_cursor = lambda: FakeCursor("33")
        try:
            resp = asyncio.run(routes_meta.handle_readyz(FakeRequest()))
            body = _body(resp)
            self.assertEqual(resp.status, 200)
            self.assertEqual(body["status"], "ready")
            self.assertEqual(body["checks"]["schema"], "33")
        finally:
            conn.get_cursor = old

    def test_readyz_bad_schema_503(self):
        import bot.infra.conn as conn
        old = conn.get_cursor
        conn.get_cursor = lambda: FakeCursor("31")
        try:
            resp = asyncio.run(routes_meta.handle_readyz(FakeRequest()))
            body = _body(resp)
            self.assertEqual(resp.status, 503)
            self.assertEqual(body["status"], "not_ready")
            self.assertEqual(body["checks"]["schema"], "31")
        finally:
            conn.get_cursor = old

    def test_readyz_db_error_503(self):
        import bot.infra.conn as conn
        old = conn.get_cursor

        def boom():
            raise RuntimeError("db down")

        conn.get_cursor = boom
        try:
            resp = asyncio.run(routes_meta.handle_readyz(FakeRequest()))
            body = _body(resp)
            self.assertEqual(resp.status, 503)
            self.assertEqual(body["checks"]["db"], "error")
            self.assertNotIn("db down", json.dumps(body))
        finally:
            conn.get_cursor = old

    def test_routes_wired(self):
        import bot.server.http_api as api
        src = open(api.__file__, encoding="utf-8").read()
        self.assertIn("/healthz", src)
        self.assertIn("/readyz", src)


if __name__ == "__main__":
    unittest.main()
