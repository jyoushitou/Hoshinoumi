# ===================== 定时执行器测试（v17.6） =====================

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


class _Ev:
    def __init__(self, args=()):
        self.args = args
        self.kind = "cron_task"


class TestCronExecutor(unittest.TestCase):
    """到点：读任务 → 生成 → 发送 → 记 last_fire"""

    def setUp(self):
        import botv.executors.cron as X
        from botv.schedule import cron

        self.X = X
        self.cron = cron
        self.sent = []
        self.prompts = []
        self.marked = []

        self.task = {"id": 7, "target_id": "822891053", "content": "叫我起床",
                     "enabled": 1, "schedule_type": "daily", "at_time": "07:30"}
        self._orig = (cron.get, X._mark)

        cron.get = lambda tid: self.task if int(tid) == 7 else None
        X._mark = lambda tid, ok=True: self.marked.append((tid, ok))

        from botv.ai import client as C
        from botv.chat import send as S

        self._ai = (C.get_character_reply, S.send_short_reply)
        C.get_character_reply = self._fake_reply
        S.send_short_reply = self._fake_send

    def tearDown(self):
        self.cron.get, self.X._mark = self._orig
        from botv.ai import client as C
        from botv.chat import send as S

        C.get_character_reply, S.send_short_reply = self._ai

    async def _fake_reply(self, prompt, tid):
        self.prompts.append(prompt)
        return "七点半了，起来吧。"

    async def _fake_send(self, *a, **k):
        self.sent.append(a)

    def test_sends_message(self):
        out = asyncio.run(self.X.handle_cron_task(_Ev(args=(7,))))
        self.assertTrue(out["ok"])
        self.assertEqual(len(self.sent), 1)
        self.assertIn("叫我起床", self.prompts[0], "提示里应带上 content")
        self.assertEqual(self.marked, [(7, True)], "应记 last_fire")

    def test_missing_task(self):
        out = asyncio.run(self.X.handle_cron_task(_Ev(args=(99,))))
        self.assertFalse(out["ok"])
        self.assertEqual(self.sent, [])

    def test_disabled_task(self):
        self.task = dict(self.task, enabled=0)
        out = asyncio.run(self.X.handle_cron_task(_Ev(args=(7,))))
        self.assertFalse(out["ok"])
        self.assertEqual(self.sent, [])

    def test_empty_content(self):
        self.task = dict(self.task, content="")
        out = asyncio.run(self.X.handle_cron_task(_Ev(args=(7,))))
        self.assertFalse(out["ok"])

    def test_no_args(self):
        out = asyncio.run(self.X.handle_cron_task(_Ev(args=())))
        self.assertFalse(out["ok"])

    def test_empty_reply_marks_failure(self):
        from botv.ai import client as C

        C.get_character_reply = lambda p, t: _async("")
        out = asyncio.run(self.X.handle_cron_task(_Ev(args=(7,))))
        self.assertFalse(out["ok"])
        self.assertEqual(self.marked, [(7, False)], "空回复也要记，避免反复重试")


async def _async(v):
    return v


if __name__ == "__main__":
    unittest.main()
