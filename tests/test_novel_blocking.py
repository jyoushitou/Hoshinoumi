# ===================== 小说链走统一线程池（v17.0.3） =====================

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


_stub_missing_deps()


class TestNovelUsesBlocking(unittest.TestCase):
    """fetch_html 必须走 run_blocking（浏览器最慢）"""

    def test_uses_run_blocking(self):
        import botv.life.novel as N

        calls = []

        async def fake_run_blocking(fn, *a, **k):
            calls.append(k)
            return "<html>fake</html>"

        orig = N._render
        N._render = lambda url: "<html>fake</html>"
        import botv.infra.blocking as B
        orig_rb = B.run_blocking
        B.run_blocking = fake_run_blocking
        try:
            html = asyncio.run(N.fetch_html("https://x/page/1"))
        finally:
            N._render = orig
            B.run_blocking = orig_rb

        self.assertEqual(html, "<html>fake</html>")
        self.assertTrue(calls, "必须经过 run_blocking")
        self.assertEqual(calls[0].get("name"), "novel")
        self.assertGreaterEqual(calls[0].get("timeout", 0), 30, "浏览器超时要放宽")


class TestOcrUsesBlocking(unittest.TestCase):
    """ocr_url 必须走 run_blocking（截图 + 识别都慢）"""

    def test_uses_run_blocking(self):
        import botv.life.ocr as O
        import botv.infra.blocking as B

        calls = []

        async def fake_run_blocking(fn, *a, **k):
            calls.append(k)
            return "识别出来的文字"

        orig = (O._shot_and_ocr, O.tesseract_ok)
        O._shot_and_ocr = lambda url: "识别出来的文字"
        O.tesseract_ok = lambda: True
        orig_rb = B.run_blocking
        B.run_blocking = fake_run_blocking
        try:
            text = asyncio.run(O.ocr_url("https://x/reader/1"))
        finally:
            O._shot_and_ocr, O.tesseract_ok = orig
            B.run_blocking = orig_rb

        self.assertEqual(text, "识别出来的文字")
        self.assertEqual(calls[0].get("name"), "ocr")
        self.assertGreaterEqual(calls[0].get("timeout", 0), 60, "OCR 超时要更宽")


if __name__ == "__main__":
    unittest.main()
