# ===================== 连发合并接入测试（v17.3 U2） =====================

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


class TestBatchable(unittest.TestCase):
    """哪些消息能进合并窗口"""

    def setUp(self):
        from botv.chat import batcher

        self.B = batcher
        self._enabled = batcher.ENABLED

    def tearDown(self):
        self.B.ENABLED = self._enabled

    def test_private_text_yes(self):
        self.B.ENABLED = True
        self.assertTrue(self.B.batchable("private", "在吗"))

    def test_group_no(self):
        self.B.ENABLED = True
        self.assertFalse(self.B.batchable("group", "在吗"))

    def test_command_no(self):
        self.B.ENABLED = True
        self.assertFalse(self.B.batchable("private", "!stats"))

    def test_empty_no(self):
        self.B.ENABLED = True
        self.assertFalse(self.B.batchable("private", "   "))

    def test_disabled_no(self):
        self.B.ENABLED = False
        self.assertFalse(self.B.batchable("private", "在吗"))

    def test_code_mode_no(self):
        self.B.ENABLED = True
        from botv.core import state as cfg

        orig = cfg.CODE_MODE
        cfg.CODE_MODE = True
        try:
            self.assertFalse(self.B.batchable("private", "写个函数"))
        finally:
            cfg.CODE_MODE = orig


class TestBatchHandler(unittest.TestCase):
    """一批消息合并成一次回复"""

    def test_single_uses_original_text(self):
        from botv.chat import batcher

        calls = []

        async def fake_reply(d, ws, text, img_md5s=None):
            calls.append(text)

        orig = batcher._handle_batch.__globals__.get("_reply_and_send")
        import botv.chat.handler as H

        H_reply = H._reply_and_send
        H._reply_and_send = fake_reply
        try:
            asyncio.run(batcher._handle_batch("1", [({"message_type": "private"}, None, "在吗", [])]))
        finally:
            H._reply_and_send = H_reply

        self.assertEqual(calls, ["在吗"])

    def test_multi_merges_with_newline(self):
        from botv.chat import batcher
        import botv.chat.handler as H

        calls = []

        async def fake_reply(d, ws, text, img_md5s=None):
            calls.append(text)

        orig = H._reply_and_send
        H._reply_and_send = fake_reply
        try:
            items = [
                ({"message_type": "private"}, None, "在吗", []),
                ({"message_type": "private"}, None, "问你个事", []),
            ]
            asyncio.run(batcher._handle_batch("1", items))
        finally:
            H._reply_and_send = orig

        self.assertEqual(calls, ["在吗\n问你个事"], "多句应合并成一段")

    def test_batcher_singleton(self):
        from botv.chat.batcher import get_batcher, set_batcher

        orig = get_batcher()
        set_batcher(None)
        try:
            b = get_batcher()
            self.assertIsNotNone(b)
            self.assertIs(b, get_batcher(), "应该是同一个实例")
        finally:
            set_batcher(orig)


if __name__ == "__main__":
    unittest.main()
