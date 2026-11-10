# ===================== 版本命令测试（v17.1） =====================

import re
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


class TestVersionInfo(unittest.TestCase):
    """版本号：来源优先级、格式、运行时长"""

    def setUp(self):
        import os

        from botv.core import version as V

        self.V = V
        self._env = os.environ.pop("NAO_VERSION", None)
        V._cache.clear()

    def tearDown(self):
        import os

        if self._env is not None:
            os.environ["NAO_VERSION"] = self._env
        self.V._cache.clear()

    def test_env_wins(self):
        import os

        os.environ["NAO_VERSION"] = "9.9.9"
        try:
            self.assertEqual(self.V.get_version(force=True), "v9.9.9")
        finally:
            os.environ.pop("NAO_VERSION", None)

    def test_env_with_v_prefix(self):
        import os

        os.environ["NAO_VERSION"] = "v1.2.3"
        try:
            self.assertEqual(self.V.get_version(force=True), "v1.2.3")
        finally:
            os.environ.pop("NAO_VERSION", None)

    def test_fallback_starts_with_v(self):
        ver = self.V.get_version(force=True)
        self.assertTrue(ver.startswith("v"), f"版本号应以 v 开头：{ver}")

    def test_describe_has_fields(self):
        text = self.V.describe()
        self.assertIn("版本", text)
        self.assertIn("已运行", text)
        self.assertIn("Python", text)

    def test_uptime_non_negative(self):
        self.assertGreaterEqual(self.V.uptime_seconds(), 0)

    def test_commit_shape(self):
        commit = self.V.get_commit()
        self.assertTrue(commit == "" or re.fullmatch(r"[0-9a-f]{4,40}", commit), commit)


class TestVersionCommand(unittest.TestCase):
    """!version 注册且能返回内容"""

    def test_registered(self):
        import botv.commands  # noqa: F401
        from botv.cmd import registry

        self.assertIn("version", registry.COMMANDS)

    def test_returns_text(self):
        import asyncio

        import botv.commands  # noqa: F401
        from botv.cmd.registry import CommandContext
        from botv.cmd import registry

        cmd = registry.COMMANDS["version"]
        ctx = CommandContext(parts=["version"], uid="1", ws=None, is_group=False, gid=0)
        out = asyncio.run(cmd.handler(ctx))
        self.assertIn("版本", out)


if __name__ == "__main__":
    unittest.main()
