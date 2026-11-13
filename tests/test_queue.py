# ===================== 优先级队列测试（v17.1.0） =====================

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


def _ev(kind="idle_read", key="k1", priority=None):
    from bot.events.base import Event, Priority

    async def noop():
        return None

    return Event(kind=kind, key=key, fn=noop,
                 priority=Priority.IDLE if priority is None else priority)


class TestEventQueue(unittest.TestCase):
    """三档优先级、去重、容量、统计"""

    def setUp(self):
        from bot.scheduler.queue import EventQueue

        self.Q = EventQueue(idle_limit=3)

    def test_put_get(self):
        ev = _ev()
        self.assertTrue(self.Q.put(ev))
        self.assertEqual(len(self.Q), 1)
        self.assertIs(self.Q.get_nowait(), ev)
        self.assertIsNone(self.Q.get_nowait())

    def test_priority_order(self):
        from bot.events.base import Priority

        idle = _ev(priority=Priority.IDLE, key="i")
        event = _ev(priority=Priority.EVENT, key="e")
        chat = _ev(priority=Priority.CHAT, key="c")
        for ev in (idle, event, chat):
            self.Q.put(ev)

        self.assertIs(self.Q.get_nowait(), chat)
        self.assertIs(self.Q.get_nowait(), event)
        self.assertIs(self.Q.get_nowait(), idle)
        self.assertIsNone(self.Q.get_nowait())

    def test_dedupe_while_inflight(self):
        a = _ev(kind="read", key="book:1")
        b = _ev(kind="read", key="book:1")
        self.assertTrue(self.Q.put(a))
        self.assertFalse(self.Q.put(b), "同 key 未完成时应丢弃")
        self.assertEqual(self.Q.stats()["dropped"], 1)

    def test_dedupe_released_after_done(self):
        a = _ev(kind="read", key="book:1")
        self.Q.put(a)
        self.Q.get_nowait()
        self.Q.done(a)
        self.assertTrue(self.Q.put(_ev(kind="read", key="book:1")), "done 之后可再次入队")

    def test_idle_capacity_drops_oldest(self):
        from bot.events.base import Priority

        for i in range(4):
            self.Q.put(_ev(kind="read", key=f"b{i}", priority=Priority.IDLE))
        # 上限 3，最早那条被丢
        self.assertEqual(self.Q.qsize(Priority.IDLE), 3)
        keys = []
        while True:
            ev = self.Q.get_nowait()
            if ev is None:
                break
            keys.append(ev.key)
        self.assertNotIn("b0", keys)
        self.assertIn("b3", keys)

    def test_chat_never_dropped_by_capacity(self):
        from bot.events.base import Priority

        for i in range(10):
            self.Q.put(_ev(kind="chat", key=f"c{i}", priority=Priority.CHAT))
        self.assertEqual(self.Q.qsize(Priority.CHAT), 10)

    def test_peek_does_not_pop(self):
        ev = _ev()
        self.Q.put(ev)
        self.assertIs(self.Q.peek(), ev)
        self.assertEqual(len(self.Q), 1)

    def test_stats_shape(self):
        self.Q.put(_ev())
        s = self.Q.stats()
        for key in ("total", "chat", "event", "idle", "inflight", "dropped", "put_total"):
            self.assertIn(key, s)
        self.assertEqual(s["total"], 1)

    def test_clear(self):
        self.Q.put(_ev())
        self.Q.clear()
        self.assertEqual(len(self.Q), 0)
        self.assertIsNone(self.Q.get_nowait())

    def test_unknown_priority_goes_idle(self):
        ev = _ev(priority=9)
        self.Q.put(ev)
        self.assertEqual(self.Q.qsize(2), 1, "未知优先级按空闲处理")


if __name__ == "__main__":
    unittest.main()
