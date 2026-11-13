# ===================== v18.18 双引擎 OCR =====================

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

from bot.life import ocr  # noqa: E402


class TestDualOCR(unittest.TestCase):
    def test_consistent_uses_tesseract(self):
        a = "她今天去了学校，路上很安静。"
        self.assertEqual(ocr.merge_ocr_results(a, a), a)

    def test_one_empty_falls_back(self):
        self.assertEqual(ocr.merge_ocr_results("", "paddle"), "paddle")
        self.assertEqual(ocr.merge_ocr_results("tess", ""), "tess")

    def test_inconsistent_marks(self):
        before = ocr.ocr_uncertain_count()
        out = ocr.merge_ocr_results("她今天去了学校", "完全不同的一串字")
        self.assertEqual(out, "她今天去了学校")
        self.assertEqual(ocr.ocr_uncertain_count(), before + 1)


if __name__ == "__main__":
    unittest.main()
