# ===================== 主动消息执行器测试（v17.1.0） =====================

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
        self.kind = "proactive_tick"


class TestProactiveExecutors(unittest.TestCase):
    """tick 只判断，say 才生成；闸门拦住时不投递"""

    def setUp(self):
        import bot.executors.proactive as P
        from bot.events import registry
        from bot.scheduler.dispatcher import Scheduler, set_scheduler

        self.P = P
        self.R = registry
        self.sched = Scheduler()
        set_scheduler(self.sched)

    def tearDown(self):
        from bot.scheduler.dispatcher import set_scheduler
        set_scheduler(None)

    def test_tick_blocked_does_not_submit(self):
        from bot.life import impulse as I

        orig = I.should_chat
        I.should_chat = lambda **kw: (False, "深夜", 0.0)
        try:
            out = asyncio.run(self.P.handle_proactive_tick(_Ev()))
        finally:
            I.should_chat = orig

        self.assertFalse(out["ok"])
        self.assertEqual(out["reason"], "深夜")
        self.assertEqual(self.sched.stats()["queue"]["total"], 0)

    def test_tick_pass_submits_say(self):
        from bot.life import impulse as I

        orig = I.should_chat
        I.should_chat = lambda **kw: (True, "ok", 0.3)
        try:
            out = asyncio.run(self.P.handle_proactive_tick(_Ev()))
        finally:
            I.should_chat = orig

        self.assertTrue(out["ok"])
        self.assertEqual(self.sched.stats()["queue"]["event"], 1, "应投递一条 P1 事件")

    def test_pick_seed_shapes(self):
        seed, tag = self.P._pick_seed()
        self.assertIsInstance(seed, str)
        self.assertIsInstance(tag, str)
        self.assertTrue(seed)

    def test_say_sends(self):
        """say 会调模型并发消息"""
        sent = []

        orig_reply = None
        try:
            from bot.ai import client as C
            orig_reply = C.get_character_reply
            C.get_character_reply = lambda prompt, tid: _async("她主动说了一句")
        except Exception:
            pass

        try:
            from bot.chat import send as S
            orig_send = S.send_short_reply
            S.send_short_reply = lambda *a, **k: _async(sent.append(a))
        except Exception:
            orig_send = None

        try:
            out = asyncio.run(self.P.handle_proactive_say(_Ev(args=("1",))))
        finally:
            if orig_reply:
                C.get_character_reply = orig_reply
            if orig_send:
                S.send_short_reply = orig_send

        self.assertTrue(out["ok"], out)
        self.assertTrue(sent, "应当发出去一条")

    def test_cancel_tick_safe(self):
        self.P.cancel_tick()
        self.P.cancel_tick()


async def _async(value):
    return value


if __name__ == "__main__":
    unittest.main()
