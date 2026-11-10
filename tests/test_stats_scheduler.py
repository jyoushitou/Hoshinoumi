# ===================== !stats 接调度器（v17.1） =====================

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


class TestStatsWithScheduler(unittest.TestCase):
    """!stats 要能看到调度器状态"""

    def _run(self):
        import botv.commands  # noqa: F401
        from botv.cmd import registry
        from botv.cmd.registry import CommandContext

        cmd = registry.COMMANDS["stats"]
        ctx = CommandContext(parts=["stats"], uid="1", ws=None, is_group=False, gid=0)
        return asyncio.run(cmd.handler(ctx))

    def test_not_started_line(self):
        from botv.scheduler.dispatcher import set_scheduler

        set_scheduler(None)
        out = self._run()
        self.assertIn("调度", out)

    def test_started_shows_queue(self):
        from botv.events import registry as R
        from botv.scheduler.dispatcher import Scheduler, set_scheduler

        snapshot = dict(R._handlers)
        if R.get("demo_stats") is None:
            @R.register("demo_stats", priority=2, timeout=5)
            async def demo(ev):
                return None
        sched = Scheduler()
        set_scheduler(sched)

        async def _boot():
            sched.start()
            sched.submit("demo_stats", "k1")
            await sched.stop()

        try:
            asyncio.run(_boot())          # 启动需要事件循环
            out = self._run()             # 停掉后仍在同一个实例上
        finally:
            set_scheduler(None)
            R._handlers.clear()
            R._handlers.update(snapshot)

        self.assertIn("调度", out)
        self.assertIn("队列 1", out, "投递的任务应出现在队列里")


if __name__ == "__main__":
    unittest.main()
