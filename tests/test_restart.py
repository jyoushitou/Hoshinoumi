# ===================== 重启熔断测试（v17.10） =====================

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


class FakeWS:
    """websockets.serve 的替身：可以指定失败几次"""

    def __init__(self, owner, fail_times, ok_after=False):
        self.owner = owner
        self.fail_times = fail_times
        self.ok_after = ok_after

    def __call__(self, *a, **k):
        outer = self

        class Ctx:
            async def __aenter__(self):
                outer.owner.calls += 1
                if outer.owner.calls <= outer.fail_times:
                    raise OSError(98, "Address already in use")
                if outer.ok_after:
                    # 模拟「启动成功后收到退出」
                    outer.owner.cfg.shutdown_event.set()
                return self

            async def __aexit__(self, *a):
                return False

        return Ctx()


class TestRestartBreaker(unittest.TestCase):
    """连续失败 N 次 → 退出；成功一次 → 计数清零"""

    def setUp(self):
        import botv.app.loop as L
        from botv.core import state as cfg

        self.L = L
        self.cfg = cfg
        self.calls = 0
        self._orig = (L.websockets.serve, L.heartbeat_monitor, L.cycle_task_run,
                      L.asyncio.sleep, cfg.shutdown_event)
        cfg.shutdown_event = asyncio.Event()
        L.heartbeat_monitor = lambda *a, **k: _noop()
        L.cycle_task_run = lambda: _noop()

        async def fast_sleep(_):
            return None

        L.asyncio.sleep = fast_sleep

    def tearDown(self):
        (self.L.websockets.serve, self.L.heartbeat_monitor, self.L.cycle_task_run,
         self.L.asyncio.sleep, self.cfg.shutdown_event) = self._orig

    def test_gives_up_after_max(self):
        """一直失败 → 10 次后返回，不再无限重启"""
        self.L.websockets.serve = FakeWS(self, fail_times=999)
        self.L.MAX_RESTARTS = 10
        asyncio.run(self.L.serve(None))
        self.assertEqual(self.calls, 10, "应该正好试 10 次")

    def test_backoff_capped(self):
        """退避不超 60 秒"""
        delays = []
        orig_sleep = self.L.asyncio.sleep

        async def record_sleep(s):
            delays.append(s)
            return None

        # serve 内部用的是 asyncio.sleep，要替换模块级 asyncio
        self.L.asyncio.sleep = record_sleep
        self.L.websockets.serve = FakeWS(self, fail_times=999)
        self.L.MAX_RESTARTS = 4
        try:
            asyncio.run(self.L.serve(None))
        finally:
            self.L.asyncio.sleep = orig_sleep

        real = [d for d in delays if d and d >= 5]
        self.assertEqual(real[:3], [5, 10, 20], "退避应为 5/10/20")
        self.assertTrue(all(d <= 60 for d in real), "不能超过 60 秒")

    def test_success_before_max(self):
        """失败 2 次后成功启动 → 正常跑起来（不触发放弃）"""
        self.L.websockets.serve = FakeWS(self, fail_times=2, ok_after=True)
        self.L.MAX_RESTARTS = 5
        asyncio.run(self.L.serve(None))
        self.assertEqual(self.calls, 3, "2 次失败 + 1 次成功")

    def test_counter_reset_after_success(self):
        """成功一次后计数清零：再跑一轮从 0 开始"""
        self.L.websockets.serve = FakeWS(self, fail_times=2, ok_after=True)
        self.L.MAX_RESTARTS = 3
        asyncio.run(self.L.serve(None))
        self.assertEqual(self.calls, 3, "不会因为在第 3 次就放弃")


async def _noop():
    return None


if __name__ == "__main__":
    unittest.main()
