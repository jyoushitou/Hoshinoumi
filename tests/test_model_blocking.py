# ===================== 模型调用走统一线程池（v17.0.3） =====================

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


class _Resp:
    status_code = 200

    def json(self):
        return {"choices": [{"message": {"content": "她回了一句"}}]}


class _Session:
    def post(self, *a, **k):
        return _Resp()


class TestDeepseekUsesBlocking(unittest.TestCase):
    """call_deepseek 必须走 run_blocking（统一线程池 + 超时 + 日志）"""

    def test_uses_run_blocking(self):
        import botv.ai.client as C

        calls = []

        async def fake_run_blocking(fn, *a, **k):
            calls.append(k)
            return fn()          # 直接在当前线程跑那个同步函数

        orig = (C.run_blocking, C.get_http_session, C.cfg.DS_API_KEY,
                C.save_ai_raw_response)
        C.run_blocking = fake_run_blocking
        C.get_http_session = lambda: _Session()
        C.cfg.DS_API_KEY = "test-key"
        C.save_ai_raw_response = lambda **kw: None
        try:
            out = asyncio.run(C.call_deepseek([{"role": "user", "content": "在吗"}], retry=1))
        finally:
            (C.run_blocking, C.get_http_session, C.cfg.DS_API_KEY,
             C.save_ai_raw_response) = orig

        self.assertEqual(out, "她回了一句")
        self.assertTrue(calls, "必须经过 run_blocking")
        self.assertIn("timeout", calls[0], "必须带超时")
        self.assertEqual(calls[0].get("name"), "deepseek")


class TestDoubaoUsesBlocking(unittest.TestCase):
    """call_doubao 也必须走 run_blocking"""

    def test_uses_run_blocking(self):
        import botv.ai.client as C

        calls = []

        async def fake_run_blocking(fn, *a, **k):
            calls.append(k)
            return fn()

        orig = (C.run_blocking, C.get_http_session, C.cfg.DOUBAO_API_KEY,
                C.save_ai_raw_response)
        C.run_blocking = fake_run_blocking
        C.get_http_session = lambda: _Session()
        C.cfg.DOUBAO_API_KEY = "test-key"
        C.save_ai_raw_response = lambda **kw: None
        try:
            out = asyncio.run(C.call_doubao([{"role": "user", "content": "在吗"}]))
        finally:
            (C.run_blocking, C.get_http_session, C.cfg.DOUBAO_API_KEY,
             C.save_ai_raw_response) = orig

        self.assertEqual(out, "她回了一句")
        self.assertEqual(calls[0].get("name"), "doubao")
        self.assertIn("timeout", calls[0])


class TestVisionUsesBlocking(unittest.TestCase):
    """describe_image 必须走 run_blocking（视觉最慢，超时放宽）"""

    def test_uses_run_blocking(self):
        import botv.ai.vision as V

        calls = []

        async def fake_run_blocking(fn, *a, **k):
            calls.append(k)
            return fn()

        class _Resp:
            status_code = 200
            text = ""

            def json(self):
                return {"choices": [{"message": {"content": "描述：一只猫\n标签：猫,窗台"}}]}

        orig = (V.run_blocking, V.prepare, V.cfg.DS_API_KEY)
        V.run_blocking = fake_run_blocking
        V.prepare = lambda img: ("FAKEB64", False, 1)      # 跳过 PIL

        class _FakeRequests:
            Session = lambda self=None: self           # noqa: E731

            def post(self, *a, **k):
                return _Resp()

            def close(self):
                pass

        # vision 是在函数里 import requests 的，改 sys.modules 才能拦到
        import requests as real_requests
        sys.modules["requests"] = _FakeRequests()
        V.cfg.DS_API_KEY = "test-key"
        try:
            out = asyncio.run(V.describe_image(b"fake-image-bytes"))
        finally:
            (V.run_blocking, V.prepare, V.cfg.DS_API_KEY) = orig
            sys.modules["requests"] = real_requests

        self.assertTrue(calls, "必须经过 run_blocking")
        self.assertEqual(calls[0].get("name"), "vision")
        self.assertGreaterEqual(calls[0].get("timeout", 0), 30, "视觉超时要放宽")
        desc, tags = out
        self.assertIn("猫", desc + "".join(tags))

if __name__ == "__main__":
    unittest.main()
