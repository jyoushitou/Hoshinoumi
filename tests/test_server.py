# ===================== HTTP 接口测试（v17.16 债三） =====================

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

    # aiohttp 不在测试环境里也能测路由逻辑
    try:
        import aiohttp  # noqa: F401
    except ImportError:
        web = module("aiohttp.web")

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

        aio = module("aiohttp")
        aio.web = web


_stub_missing_deps()


class FakeRequest:
    """aiohttp Request 的最小替身"""

    def __init__(self, query=None, headers=None):
        self.query = query or {}
        self.headers = headers or {}


def _body(resp):
    """json_response 返回的 Response 取出 dict"""
    try:
        return json.loads(resp.text)
    except Exception:
        return json.loads(resp.body.decode("utf-8"))


class TestHealthAndStatus(unittest.TestCase):
    """health / status：结构、字段、不泄漏密钥"""

    def setUp(self):
        from botv.server import routes_meta

        self.R = routes_meta
        self._orig = routes_meta.counts if hasattr(routes_meta, "counts") else None
        import botv.infra.repo_query as RQ

        self.RQ = RQ
        self._orig_counts = RQ.counts
        RQ.counts = lambda tables=None, cursor=None: {
            "images": 3, "user_memory": 5, "events": 7,
            "logs": 9, "global_keywords": 11, "ai_raw_responses": 13,
        }

    def tearDown(self):
        self.RQ.counts = self._orig_counts

    def test_health(self):
        import asyncio

        resp = asyncio.run(self.R.handle_health(FakeRequest()))
        body = _body(resp)
        self.assertEqual(body["status"], "ok")
        self.assertIn("timestamp", body)

    def test_status_counts(self):
        import asyncio

        resp = asyncio.run(self.R.handle_status(FakeRequest()))
        body = _body(resp)
        self.assertEqual(body["status"], "running")
        self.assertEqual(body["stats"]["images"], 3)
        self.assertEqual(body["stats"]["memories"], 5)
        self.assertEqual(body["stats"]["ai_responses"], 13)

    def test_status_has_runtime_block(self):
        import asyncio

        body = _body(asyncio.run(self.R.handle_status(FakeRequest())))
        for key in ("dialogue_targets", "global_keywords", "stickers", "daily_triggers"):
            self.assertIn(key, body["runtime"])

    def test_status_no_secrets(self):
        """不能把 API key / 数据库密码吐出来"""
        import asyncio

        body = _body(asyncio.run(self.R.handle_status(FakeRequest())))
        text = json.dumps(body, ensure_ascii=False).lower()
        for bad in ("sk-", "password", "secret", "api_key"):
            self.assertNotIn(bad, text, f"响应里不该出现 {bad}")

    def test_status_db_failure_json(self):
        """统计失败要返回 JSON 错误，不是抛异常"""
        import asyncio

        def boom(tables=None, cursor=None):
            raise RuntimeError("db down")

        self.RQ.counts = boom
        resp = asyncio.run(self.R.handle_status(FakeRequest()))
        body = _body(resp)
        self.assertEqual(body["error"], "db_query_failed")


class TestUsageAndToken(unittest.TestCase):
    """usage / token：参数边界、token 不回显整串"""

    def setUp(self):
        from botv.server import routes_meta

        self.R = routes_meta
        # routes_meta 里是 from ... import，要 patch 它自己的名字
        self._orig_usage = routes_meta.get_recent_usage
        routes_meta.get_recent_usage = lambda limit=10: [
            {"model_name": "deepseek-flash", "prompt_tokens": 10,
             "completion_tokens": 20, "total_tokens": 30,
             "status": "ok", "created_at": "2026-11-11 10:00:00"}
        ]

    def tearDown(self):
        self.R.get_recent_usage = self._orig_usage

    def test_usage_default(self):
        import asyncio

        body = _body(asyncio.run(self.R.handle_usage(FakeRequest())))
        self.assertIn("records", body)
        self.assertIn("summary", body)

    def test_usage_bad_limit(self):
        import asyncio

        body = _body(asyncio.run(self.R.handle_usage(FakeRequest({"limit": "abc"}))))
        self.assertIn("summary", body)

    def test_usage_limit_clamped(self):
        import asyncio

        seen = []
        self.R.get_recent_usage = lambda limit=10: seen.append(limit) or []
        body = _body(asyncio.run(self.R.handle_usage(FakeRequest({"limit": "999"}))))
        self.assertEqual(seen[0], 100, "上限应钳到 100")

    def test_token_masked(self):
        from botv.server import config as apicfg

        text = apicfg.format_api_token_info()
        self.assertIn("API", text)
        self.assertIn("Token", text)


class TestRouteWiring(unittest.TestCase):
    """路由装配：http_api 里应挂上 health/status/usage/chat"""

    def test_handlers_wired(self):
        import botv.server.http_api as api

        src = open(api.__file__, encoding="utf-8").read()
        for path in ("/health", "/status", "/usage", "/chat"):
            self.assertIn(path, src, f"路由里应有 {path}")

    def test_meta_handlers_callable(self):
        from botv.server import routes_meta

        for fn in (routes_meta.handle_health, routes_meta.handle_status,
                   routes_meta.handle_usage):
            self.assertTrue(callable(fn))


if __name__ == "__main__":
    unittest.main()
