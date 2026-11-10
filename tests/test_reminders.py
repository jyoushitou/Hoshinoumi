# ===================== 日程/待办执行器测试（v17.1.0） =====================

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
        self.kind = "agenda_remind"


class TestReminders(unittest.TestCase):
    """日程提醒与待办回访：生成 → 发送 → 标记完成"""

    def setUp(self):
        import botv.executors.reminders as RM
        from botv.scheduler.dispatcher import Scheduler, set_scheduler

        self.RM = RM
        self.sched = Scheduler()
        set_scheduler(self.sched)
        self.sent = []
        self.marked = []

        from botv.ai import client as C
        from botv.chat import send as SEND

        self._orig = (C.get_character_reply, SEND.send_short_reply)
        C.get_character_reply = lambda prompt, tid: _async("提醒一句")
        SEND.send_short_reply = lambda *a, **k: _async(self.sent.append(a))

    def tearDown(self):
        from botv.ai import client as C
        from botv.chat import send as SEND
        from botv.scheduler.dispatcher import set_scheduler

        C.get_character_reply, SEND.send_short_reply = self._orig
        set_scheduler(None)

    def test_agenda_handler_sends(self):
        from botv.life import agenda

        orig = agenda.mark_reminded
        agenda.mark_reminded = lambda i: self.marked.append(i)
        try:
            out = asyncio.run(self.RM.handle_agenda(_Ev(args=("面试", 7))))
        finally:
            agenda.mark_reminded = orig

        self.assertTrue(out["ok"])
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.marked, [7], "发完要标记已提醒")

    def test_pending_handler_sends(self):
        out = asyncio.run(self.RM.handle_pending(_Ev(args=("说好一起吃饭", 3))))
        self.assertTrue(out["ok"])
        self.assertEqual(len(self.sent), 1)

    def test_submit_dedupe(self):
        self.assertTrue(self.RM.submit_agenda("面试", 7))
        self.assertFalse(self.RM.submit_agenda("面试", 7), "同一条不应重复投递")
        self.assertTrue(self.RM.submit_pending("吃饭", 3))

    def test_empty_reply_not_sent(self):
        from botv.ai import client as C

        C.get_character_reply = lambda prompt, tid: _async("")
        out = asyncio.run(self.RM.handle_agenda(_Ev(args=("面试", 7))))
        self.assertFalse(out["ok"])
        self.assertEqual(self.sent, [])


async def _async(value):
    return value


if __name__ == "__main__":
    unittest.main()
