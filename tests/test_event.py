# ===================== 事件对象测试（v17.1.0） =====================

import asyncio
import time
import unittest


class TestEvent(unittest.TestCase):
    """Event：去重键、优先级、存活时间、默认值"""

    def _make(self, **kw):
        from botv.events.base import Event

        async def noop():
            return None

        params = {"kind": "idle_read", "key": "book:1", "fn": noop}
        params.update(kw)
        return Event(**params)

    def test_defaults(self):
        from botv.events.base import DEFAULT_TIMEOUT, Priority

        ev = self._make()
        self.assertEqual(ev.priority, Priority.IDLE)
        self.assertEqual(ev.retries, 1)
        self.assertEqual(ev.timeout, DEFAULT_TIMEOUT)
        self.assertTrue(ev.id)

    def test_dedupe_key(self):
        ev = self._make(kind="schedule", key="c1")
        self.assertEqual(ev.dedupe_key(), "schedule:c1")

    def test_ids_unique(self):
        a, b = self._make(), self._make()
        self.assertNotEqual(a.id, b.id)

    def test_age(self):
        ev = self._make()
        later = time.time() + 10
        self.assertGreaterEqual(ev.age(later), 10)

    def test_priority_order(self):
        from botv.events.base import Priority

        self.assertLess(Priority.CHAT, Priority.EVENT)
        self.assertLess(Priority.EVENT, Priority.IDLE)
        self.assertEqual(int(Priority.CHAT), 0)

    def test_fn_callable(self):
        ev = self._make()
        self.assertEqual(asyncio.run(ev.fn()), None)

    def test_str_readable(self):
        ev = self._make(kind="chat", key="822891053")
        text = str(ev)
        self.assertIn("chat:822891053", text)
        self.assertIn("p=2", text)


if __name__ == "__main__":
    unittest.main()
