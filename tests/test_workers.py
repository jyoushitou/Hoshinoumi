# ===================== Worker 池测试（v17.1.0） =====================

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


_stub_missing_deps()


def _make_pool(idle=2, event=1):
    from botv.scheduler.queue import EventQueue
    from botv.scheduler.workers import WorkerPool

    q = EventQueue(idle_limit=20)
    return q, WorkerPool(q, idle_workers=idle, event_workers=event)


def _ev(kind="read", key=None, fn=None, priority=None, timeout=2.0, retries=1):
    from botv.events.base import Event, Priority

    async def noop():
        return None

    return Event(kind=kind, key=key or kind, fn=fn or noop,
                 priority=Priority.IDLE if priority is None else priority,
                 timeout=timeout, retries=retries)


class TestWorkerPool(unittest.TestCase):
    """执行、优先级、超时、重试、熔断、并行"""

    def test_executes_event(self):
        q, pool = _make_pool()
        ran = []

        async def job():
            ran.append(1)

        async def main():
            pool.start()
            q.put(_ev(fn=job))
            await asyncio.sleep(0.3)
            await pool.stop()

        asyncio.run(main())
        self.assertEqual(ran, [1])
        self.assertEqual(pool.stats()["done"], 1)

    def test_chat_before_idle(self):
        """快车道先取 CHAT，慢车道不会抢走它"""
        from botv.events.base import Priority

        q, pool = _make_pool(idle=0, event=1)
        order = []

        async def a():
            order.append("idle")

        async def b():
            order.append("chat")

        q.put(_ev(kind="i", key="i", fn=a, priority=Priority.IDLE))
        q.put(_ev(kind="c", key="c", fn=b, priority=Priority.CHAT))
        self.assertIn(q.get_from((Priority.CHAT, Priority.EVENT)).kind, ("c",))

    def test_timeout_counted(self):
        q, pool = _make_pool()
        timeline = []

        async def slow():
            await asyncio.sleep(1.0)
            timeline.append("late")

        async def main():
            pool.start()
            q.put(_ev(kind="slow", key="s", fn=slow, timeout=0.1))
            await asyncio.sleep(0.4)
            await pool.stop()

        asyncio.run(main())
        st = pool.stats()
        self.assertEqual(st["timeouts"], 1)
        self.assertEqual(st["failed"], 1)
        self.assertEqual(timeline, [], "超时的任务不该跑完")

    def test_retry_then_success(self):
        from botv.scheduler import policy
        orig = policy.RETRY_BASE_DELAY
        policy.RETRY_BASE_DELAY = 0.01
        self.addCleanup(lambda: setattr(policy, "RETRY_BASE_DELAY", orig))

        q, pool = _make_pool()
        attempts = []

        async def flaky():
            attempts.append(1)
            if len(attempts) < 2:
                raise RuntimeError("第一次失败")

        async def main():
            pool.start()
            q.put(_ev(kind="flaky", key="f", fn=flaky, retries=2, timeout=1.0))
            await asyncio.sleep(0.3)
            await pool.stop()

        asyncio.run(main())
        st = pool.stats()
        self.assertEqual(len(attempts), 2, "应该重试一次")
        self.assertEqual(st["done"], 1)
        self.assertEqual(st["retries"], 1)

    def test_breaker_skips(self):
        """连续失败 3 次后，第 4 个同 kind 直接跳过（不执行）"""
        q, pool = _make_pool(idle=1, event=1)
        calls = []

        async def boom():
            calls.append(1)
            raise RuntimeError("坏了")

        async def main():
            pool.start()
            for i in range(4):
                q.put(_ev(kind="boom", key=f"b{i}", fn=boom, retries=1, timeout=1.0))
            await asyncio.sleep(0.6)
            await pool.stop()

        asyncio.run(main())
        # 前 3 个真的执行了，第 4 个被熔断挡掉
        self.assertEqual(len(calls), 3, f"熔断后不该再执行（实际 {len(calls)} 次）")
        self.assertTrue(pool.stats()["breaker"]["open_kinds"])

    def test_parallel_idle_tasks(self):
        """两个空闲任务并行：总耗时接近单个"""
        import time as _t

        q, pool = _make_pool(idle=2, event=1)
        stamps = []

        async def slow_job(tag):
            started = _t.time()
            await asyncio.sleep(0.3)
            stamps.append((tag, started, _t.time()))

        async def main():
            pool.start()
            q.put(_ev(kind="a", key="a", fn=lambda: slow_job("a")))
            q.put(_ev(kind="b", key="b", fn=lambda: slow_job("b")))
            await asyncio.sleep(0.8)
            await pool.stop()

        asyncio.run(main())
        self.assertEqual(len(stamps), 2)
        # 两段执行区间应该有重叠
        (_, s1, e1), (_, s2, e2) = stamps
        overlap = min(e1, e2) - max(s1, s2)
        self.assertGreater(overlap, 0.1, "两个空闲任务应当并行")

    def test_dedupe_released_after_run(self):
        q, pool = _make_pool()

        async def job():
            return None

        async def main():
            pool.start()
            q.put(_ev(kind="k", key="same", fn=job))
            await asyncio.sleep(0.2)
            ok = q.put(_ev(kind="k", key="same", fn=job))
            await asyncio.sleep(0.2)
            await pool.stop()
            return ok

        self.assertTrue(asyncio.run(main()), "任务完成后同 key 应能再次入队")

    def test_stats_shape(self):
        q, pool = _make_pool()
        st = pool.stats()
        for key in ("running", "done", "failed", "timeouts", "retries",
                    "by_kind", "breaker", "queue", "slots"):
            self.assertIn(key, st)


if __name__ == "__main__":
    unittest.main()
