# ===================== v32.4 多行命令 =====================
import asyncio
import sys
import types
import unittest
from unittest import mock

try:
    import jieba  # noqa: F401
except ImportError:
    m = types.ModuleType("jieba")
    m.lcut = lambda s: list(s)
    sys.modules["jieba"] = m

from bot.commands import split_commands


class TestSplitCommands(unittest.TestCase):
    def test_two_commands(self):
        self.assertEqual(split_commands("!ping\n!version"), ["!ping", "!version"])

    def test_continuation(self):
        self.assertEqual(split_commands("!say 三句\n第一句\n第二句"),
                         ["!say 三句\n第一句\n第二句"])

    def test_normal_chat_not_split(self):
        self.assertEqual(split_commands("你好\n!ping"), ["你好\n!ping"])

    def test_multiple_with_continuation(self):
        self.assertEqual(split_commands("!say a\nb\n!ping"),
                         ["!say a\nb", "!ping"])


if __name__ == "__main__":
    unittest.main()
