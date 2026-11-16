# ===================== v31.3 动态帮助 =====================
import asyncio
import sys
import types
import unittest

try:
    import jieba  # noqa: F401
except ImportError:
    m = types.ModuleType("jieba")
    m.lcut = lambda s: list(s)
    sys.modules["jieba"] = m

import bot.commands  # noqa: F401
from bot.cmd import registry
from bot.cmd.basic import cmd_help
from bot.cmd.formatters import build_cmd_help
from bot.cmd.registry import CommandContext


class TestHelpV313(unittest.TestCase):
    def test_grouped_has_new_commands(self):
        text = build_cmd_help()
        for name in ("plugin", "book", "history", "gw"):
            self.assertIn(f"!{name}", text)

    def test_single_command(self):
        text = build_cmd_help("plugin")
        self.assertIn("!plugin", text)
        self.assertIn("安装", text)

    def test_all_matches_registry(self):
        text = build_cmd_help("all")
        for name in registry.COMMANDS:
            self.assertIn(f"!{name}", text)
        self.assertIn(str(len(registry.COMMANDS)), text)

    def test_unknown_does_not_crash(self):
        self.assertIn("没有这个命令", build_cmd_help("nope"))

    def test_command_handler(self):
        ctx = CommandContext(parts=["help", "plugin"], uid="1",
                             ws=None, is_group=False, gid=0)
        self.assertIn("!plugin", asyncio.run(cmd_help(ctx)))


if __name__ == "__main__":
    unittest.main()
