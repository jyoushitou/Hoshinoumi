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
        import bot.executors.cron as X
        from bot.schedule import cron

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

        from bot.ai import client as C
        from bot.chat import send as S

        self._ai = (C.get_character_reply, S.send_short_reply)
        C.get_character_reply = self._fake_reply
        S.send_short_reply = self._fake_send

    def tearDown(self):
        self.cron.get, self.X._mark = self._orig
        from bot.ai import client as C
        from bot.chat import send as S

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
        from bot.ai import client as C

        C.get_character_reply = lambda p, t: _async("")
        out = asyncio.run(self.X.handle_cron_task(_Ev(args=(7,))))
        self.assertFalse(out["ok"])
        self.assertEqual(self.marked, [(7, False)], "空回复也要记，避免反复重试")


async def _async(v):
    return v



    def test_scene_prefix_routes_to_scene_executor(self):
        """content 以 scene: 开头 → 走场景执行器（带提示词/配图）"""
        from bot.executors import schedule as S
        import bot.executors.cron as X

        called = []

        async def fake_scene(ev):
            called.append(ev.args)
            return {"ok": True, "scene": ev.args[0]}

        orig = S.handle_schedule_scene
        S.handle_schedule_scene = fake_scene
        self.task = dict(self.task, content="scene:催起床")
        try:
            out = asyncio.run(X.handle_cron_task(_Ev(args=(7,))))
        finally:
            S.handle_schedule_scene = orig

        self.assertTrue(out["ok"])
        self.assertEqual(called, [("催起床",)], "应转给场景执行器")
        self.assertEqual(self.sent, [], "场景执行器自己发，不走这里")

if __name__ == "__main__":
    unittest.main()
