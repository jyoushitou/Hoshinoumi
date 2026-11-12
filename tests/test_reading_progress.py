# ===================== v18.16 读书进度落库 =====================

import json
import sys
import types
import unittest
from unittest.mock import patch


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

from botv.infra import repo_memory  # noqa: E402


class TestReadingProgress(unittest.TestCase):
    def test_save_splits_books(self):
        calls = []

        def fake_dual(kind, tid, payload):
            calls.append(json.loads(payload))
            return True

        payload = {"books": [
            {"title": "书A", "url": "http://a", "last_no": 2, "last_title": "第二章"},
            {"title": "书B", "url": "http://b", "last_no": 5},
        ]}
        with patch.object(repo_memory, "dual_write", fake_dual):
            repo_memory.save_reading("1", json.dumps(payload))
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]["book_url"], "http://a")
        self.assertEqual(calls[0]["last_no"], 2)
        self.assertEqual(calls[1]["book_url"], "http://b")
        self.assertEqual(calls[1]["last_no"], 5)

    def test_json_table_has_book_url(self):
        _table, fields = repo_memory._JSON_TABLES["reading"]
        self.assertIn("book_url", fields)


if __name__ == "__main__":
    unittest.main()
