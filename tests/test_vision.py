# ===================== 视觉修复测试（v18.1） =====================

import asyncio
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


class TestProviders(unittest.TestCase):
    """key 取值顺序 + 默认端点"""

    def setUp(self):
        from botv.ai import vision

        self.V = vision
        self._orig = (self.V.cfg.DS_API_KEY, self.V.cfg.DOUBAO_API_KEY)
        self.V.cfg.DS_API_KEY = ""
        self.V.cfg.DOUBAO_API_KEY = ""
        for k in ("NAO_VISION_KEY", "NAO_VISION_URL", "NAO_VISION_MODEL"):
            __import__("os").environ.pop(k, None)

    def tearDown(self):
        self.V.cfg.DS_API_KEY, self.V.cfg.DOUBAO_API_KEY = self._orig

    def test_default_is_doubao(self):
        self.V.cfg.DOUBAO_API_KEY = "doubao-key"
        provs = self.V.providers()
        self.assertEqual(provs[0]["name"], "豆包")
        self.assertIn("ark.cn-beijing.volces.com", provs[0]["url"])
        self.assertIn("doubao-seed-2.1-lite-260915", provs[0]["model"])

    def test_fallback_to_deepseek(self):
        self.V.cfg.DOUBAO_API_KEY = "d"
        self.V.cfg.DS_API_KEY = "ds"
        names = [p["name"] for p in self.V.providers()]
        self.assertEqual(names, ["豆包", "DeepSeek"], "应有降级链")

    def test_only_deepseek_when_no_doubao(self):
        self.V.cfg.DS_API_KEY = "ds"
        names = [p["name"] for p in self.V.providers()]
        self.assertEqual(names, ["DeepSeek"])

    def test_dedicated_key_wins(self):
        import os

        self.V.cfg.DOUBAO_API_KEY = "doubao"
        os.environ["NAO_VISION_KEY"] = "special"
        self.assertEqual(self.V.vision_key(), "special")
        os.environ.pop("NAO_VISION_KEY", None)

    def test_no_key_no_provider(self):
        self.assertEqual(self.V.providers(), [])


class TestDescribeFallback(unittest.TestCase):
    """第一段失败自动降级第二段；全失败返回 None"""

    def setUp(self):
        from botv.ai import vision

        self.V = vision
        self.V.cfg.DOUBAO_API_KEY = "d"
        self.V.cfg.DS_API_KEY = "ds"
        self.V.prepare = lambda img, **kw: ("B64", False, 1)
        self.calls = []

    def _install(self, responses):
        V = self.V
        seq = list(responses)

        class Resp:
            def __init__(self, code, text="", body=None):
                self.status_code = code
                self.text = text
                self._body = body or {}

            def json(self):
                return self._body

        class Sess:
            def post(self, url, headers=None, data=None, timeout=None):
                self_url = url
                seq_item = seq.pop(0) if seq else (500, "", {})
                self_url_log = self_url
                V._last_urls.append(self_url_log)
                return Resp(*seq_item)

            def close(self):
                pass

        V._last_urls = []

        async def fake_run(fn, *a, **k):
            return fn()

        V.run_blocking = fake_run
        sys.modules["requests"] = types.SimpleNamespace(Session=Sess)

        def _fake_run_blocking(fn, *a, **kw):
            calls = []
            return fn()

        async def _async_run(fn, *a, **kw):
            self.calls.append(1)
            return fn()

        V.run_blocking = _async_run

    def test_falls_back_to_second(self):
        ok = {"choices": [{"message": {"content": "描述：一只橘猫\n标签：猫,窗台"}}]}
        self._install([(400, "image_url not supported", {}), (200, "", ok)])
        out = asyncio.run(self.V.describe_image(b"img"))
        self.assertEqual(out[0], "一只橘猫")
        self.assertEqual(len(self.calls), 2, "应尝试两次")

    def test_all_fail_returns_none(self):
        self._install([(401, "bad key", {}), (400, "nope", {})])
        out = asyncio.run(self.V.describe_image(b"img"))
        self.assertEqual(out, (None, []))

    def test_empty_bytes(self):
        self.assertEqual(asyncio.run(self.V.describe_image(b"")), (None, []))


if __name__ == "__main__":
    unittest.main()
