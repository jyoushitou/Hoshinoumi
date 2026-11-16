# ===================== v32.3 钩子 suffix =====================
import asyncio
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path

try:
    import jieba  # noqa: F401
except ImportError:
    m = types.ModuleType("jieba")
    m.lcut = lambda s: list(s)
    sys.modules["jieba"] = m

from bot.cmd.cron_cmd import cmd_cron
from bot.cmd.registry import CommandContext
from bot.schedule import cron
from bot.schedule.extract import parse_hook_modify


class TestHookSuffixV323(unittest.TestCase):
    def setUp(self):
        from bot.infra import conn, schema
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        conn.configure(backend="sqlite", sqlite_path=str(Path(self.tmp) / "m.db"))
        self.c = conn.get_cursor()
        schema.ensure_tables(self.c, names=["cron_tasks", "bot_meta"])
        try:
            self.c.execute("ALTER TABLE cron_tasks ADD COLUMN user_id VARCHAR(64) DEFAULT '__owner__'")
        except Exception:
            pass
        self.c.connection.commit()
        from scripts import migrate_v31
        migrate_v31.apply(self.c)

    def tearDown(self):
        try:
            self.c.close()
        except Exception:
            pass
        from bot.infra import conn
        conn.configure(backend=None, sqlite_path=None, mysql_config=None)

    def test_schema31_and_append(self):
        a = cron.add("1", "daily", "scene:提醒晚餐", at_time="16:40")
        b = cron.add("1", "daily", "scene:提醒点外卖", at_time="10:40")
        cron.add("1", "daily", "scene:催睡觉", at_time="23:00")
        hits = cron.append_suffix("吃饭", "少吃点")
        self.assertEqual({i for i, _ in hits}, {a, b})
        self.assertEqual(cron.get(a)["suffix"], "少吃点")
        self.assertEqual(cron.get(b)["suffix"], "少吃点")
        cron.set_suffix(a, "")
        self.assertIsNone(cron.get(a)["suffix"])

    def test_parse_hook_modify(self):
        self.assertEqual(parse_hook_modify("提醒我吃饭的时候，让我少吃点，我要减肥"),
                         ("吃饭", "少吃点，我要减肥"))
        self.assertIsNone(parse_hook_modify("提醒我七点吃饭"))

    def test_command_append(self):
        cron.add("1", "daily", "scene:提醒晚餐", at_time="16:40")
        ctx = CommandContext(parts=["cron", "append", "吃饭", "少吃点"], uid="1",
                             ws=None, is_group=False, gid=0)
        out = asyncio.run(cmd_cron(ctx))
        self.assertIn("已给", out)


if __name__ == "__main__":
    unittest.main()
