# ===================== 命令通道测试（v17.2 U4） =====================

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


async def _ok(*a, **k):
    return "ok"


class TestCommandChannel(unittest.TestCase):
    """执行、超时、错误、并发上限、统计"""

    def test_run_ok(self):
        from botv.cmd.channel import CommandChannel

        ch = CommandChannel(timeout=1)
        ok, out = asyncio.run(ch.run("ping", _ok))
        self.assertTrue(ok)
        self.assertEqual(out, "ok")
        self.assertEqual(ch.stats()["count"], 1)

    def test_timeout(self):
        from botv.cmd.channel import CommandChannel

        async def slow(*a):
            await asyncio.sleep(1)

        ch = CommandChannel(timeout=0.05)
        ok, out = asyncio.run(ch.run("slow", slow))
        self.assertFalse(ok)
        self.assertIn("超时", out)
        self.assertEqual(ch.stats()["timeouts"], 1)

    def test_error(self):
        from botv.cmd.channel import CommandChannel

        async def boom(*a):
            raise RuntimeError("炸了")

        ch = CommandChannel(timeout=1)
        ok, out = asyncio.run(ch.run("boom", boom))
        self.assertFalse(ok)
        self.assertIn("出错", out)
        self.assertEqual(ch.stats()["errors"], 1)

    def test_concurrency_limited(self):
        from botv.cmd.channel import CommandChannel

        running = {"now": 0, "max": 0}

        async def job(*a):
            running["now"] += 1
            running["max"] = max(running["max"], running["now"])
            await asyncio.sleep(0.05)
            running["now"] -= 1

        ch = CommandChannel(timeout=2, max_concurrent=2)

        async def main():
            await asyncio.gather(*[ch.run("j", job) for _ in range(6)])

        asyncio.run(main())
        self.assertLessEqual(running["max"], 2, "并发度应受信号量限制")

    def test_stats_slowest(self):
        from botv.cmd.channel import CommandChannel

        async def fast(*a):
            return 1

        async def slow(*a):
            await asyncio.sleep(0.05)

        ch = CommandChannel(timeout=1)

        async def main():
            await ch.run("fast", fast)
            await ch.run("slow", slow)

        asyncio.run(main())
        self.assertEqual(ch.stats()["slowest"]["name"], "slow")

    def test_describe_before_any(self):
        from botv.cmd.channel import CommandChannel

        ch = CommandChannel()
        self.assertIn("还没执行", ch.describe())

    def test_describe_after(self):
        from botv.cmd.channel import CommandChannel

        ch = CommandChannel(timeout=1)
        asyncio.run(ch.run("ping", _ok))
        text = ch.describe()
        self.assertIn("命令", text)
        self.assertIn("平均", text)


if __name__ == "__main__":
    unittest.main()
