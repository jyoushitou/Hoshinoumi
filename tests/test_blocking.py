# ===================== run_blocking 测试（v17.0.1） =====================

import asyncio
import sys
import time
import types
import unittest


def _stub_missing_deps():
    """单独跑本文件时缺依赖打个桩（和 test_smoke 同款）"""
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


class TestRunBlocking(unittest.TestCase):
    """阻塞调用丢线程池：结果正确、异常透传、超时不卡循环、并发真的并行"""

    def test_returns_value(self):
        from botv.infra.blocking import run_blocking

        out = asyncio.run(run_blocking(lambda: 42))
        self.assertEqual(out, 42)

    def test_passes_args_and_kwargs(self):
        from botv.infra.blocking import run_blocking

        def add(a, b=0):
            return a + b

        out = asyncio.run(run_blocking(add, 1, b=2))
        self.assertEqual(out, 3)

    def test_exception_propagates(self):
        from botv.infra.blocking import run_blocking

        def boom():
            raise ValueError("炸了")

        with self.assertRaises(ValueError):
            asyncio.run(run_blocking(boom))

    def test_timeout_raises(self):
        from botv.infra.blocking import run_blocking

        def slow():
            time.sleep(0.5)
            return "done"

        async def main():
            return await run_blocking(slow, timeout=0.05)

        with self.assertRaises(asyncio.TimeoutError):
            asyncio.run(main())

    def test_loop_not_blocked(self):
        """阻塞函数执行期间，事件循环还能跑别的协程"""
        from botv.infra.blocking import run_blocking

        ticks = []

        async def ticker():
            for i in range(5):
                ticks.append(i)
                await asyncio.sleep(0.02)

        async def main():
            await asyncio.gather(
                run_blocking(time.sleep, 0.2),
                ticker(),
            )

        asyncio.run(main())
        self.assertEqual(len(ticks), 5, "循环被阻塞时 ticker 跑不完")

    def test_true_parallel(self):
        """两个 0.2 秒的阻塞任务，总耗时应该接近 0.2 而不是 0.4"""
        from botv.infra.blocking import run_blocking

        async def main():
            started = time.time()
            await asyncio.gather(
                run_blocking(time.sleep, 0.2),
                run_blocking(time.sleep, 0.2),
            )
            return time.time() - started

        elapsed = asyncio.run(main())
        self.assertLess(elapsed, 0.36, f"没有并行（用了 {elapsed:.2f}s）")


if __name__ == "__main__":
    unittest.main()
