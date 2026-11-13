# ===================== v19.5 日程钩子去重 =====================
import time
import unittest

from tests.test_chat import _stub_missing_deps

_stub_missing_deps()

from botv.schedule import items


class _Handle:
    def __init__(self, n):
        self.n = n
        self.cancelled = False

    def cancel(self):
        self.cancelled = True


class _Loop:
    def __init__(self):
        self.calls = 0

    def time(self):
        return 0.0

    def call_at(self, when, fn, *args):
        self.calls += 1
        return _Handle(self.calls)


class TestItemsHooks(unittest.TestCase):
    def setUp(self):
        items._handles.clear()
        self.loop = _Loop()
        self._orig = items.asyncio.get_running_loop
        items.asyncio.get_running_loop = lambda: self.loop

    def tearDown(self):
        items.asyncio.get_running_loop = self._orig
        items._handles.clear()

    def test_only_missing_keeps_existing(self):
        h1 = items.schedule("agenda", 1, time.time() + 60, "x")
        self.assertIsNotNone(h1)
        h2 = items.schedule("agenda", 1, time.time() + 60, "x", only_missing=True)
        self.assertIs(h1, h2)
        self.assertEqual(self.loop.calls, 1)

    def test_replace_default(self):
        h1 = items.schedule("agenda", 2, time.time() + 60, "x")
        h2 = items.schedule("agenda", 2, time.time() + 120, "y")
        self.assertIsNot(h1, h2)
        self.assertTrue(h1.cancelled)
        self.assertEqual(self.loop.calls, 2)

    def test_cancel_removes(self):
        items.schedule("pending", 3, time.time() + 60, "x")
        self.assertTrue(items.cancel("pending", 3))
        self.assertNotIn("pending:3", items._handles)


if __name__ == "__main__":
    unittest.main()
