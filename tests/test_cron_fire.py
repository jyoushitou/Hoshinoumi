# ===================== 定时钩子投递测试（L15） =====================

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


class TestFireWithoutScheduler(unittest.TestCase):
    """L15：命令建的钩子没传 scheduler，到点也必须投递"""

    def setUp(self):
        from botv.schedule import cron
        from botv.scheduler import dispatcher

        self.C = cron
        self.D = dispatcher
        self.sent = []
        self.C.cancel_all()
        self.task = {"id": 42, "schedule_type": "once",
                     "once_at": "2099-01-01 00:00:00", "jitter_min": 0,
                     "enabled": 1, "target_id": "1", "content": "测试"}
        self._orig = (cron.get, cron.set_next, cron.set_enabled)

        cron.get = lambda tid: dict(self.task)
        cron.set_next = lambda tid, ts: True
        cron.set_enabled = lambda tid, on: True

        class FakeSched:
            def submit(sched_self, kind, key, args=(), **kw):
                self.sent.append((kind, key, args))
                return True

        self.fake = FakeSched()
        self._orig_get = dispatcher.get_scheduler
        dispatcher.get_scheduler = lambda: self.fake

    def tearDown(self):
        self.C.get, self.C.set_next, self.C.set_enabled = self._orig
        self.D.get_scheduler = self._orig_get
        self.C.cancel_all()

    def test_fires_without_scheduler_arg(self):
        """关键：schedule_one(task) 不传 scheduler，到点仍要 submit"""
        loop = asyncio.new_event_loop()
        try:
            h = self.C.schedule_one(self.task, loop)    # 传 loop，不传 scheduler
            self.assertIsNotNone(h)
            h._callback()                                # 直接触发
        finally:
            loop.close()
        self.assertEqual(len(self.sent), 1, "必须投递一次")
        self.assertEqual(self.sent[0][0], "cron_task")
        self.assertEqual(self.sent[0][2], (42,))

    def test_explicit_scheduler_still_wins(self):
        """传了 scheduler 就用传的，不碰全局"""
        calls = []

        class Explicit:
            def submit(s, kind, key, args=(), **kw):
                calls.append(kind)
                return True

            # 避免重排时炸
        loop = asyncio.new_event_loop()
        try:
            h = self.C.schedule_one(self.task, loop, Explicit())
            h._callback()
        finally:
            loop.close()
        self.assertEqual(calls, ["cron_task"])
        self.assertEqual(self.sent, [], "不该用全局调度器")


if __name__ == "__main__":
    unittest.main()
