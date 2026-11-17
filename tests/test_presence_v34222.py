# ===================== v34.2.2.2 手动覆盖 =====================
import asyncio
import shutil
import tempfile
import unittest
from pathlib import Path

from bot.cmd.presence_cmd import cmd_doing
from bot.cmd.registry import CommandContext
from bot.infra import conn, schema
from bot.life import presence
from scripts import migrate_v32


class TestManualV34222(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.mkdtemp(); self.addCleanup(shutil.rmtree,self.tmp,True)
        conn.configure(backend="sqlite",sqlite_path=str(Path(self.tmp)/"m.db"))
        c=conn.get_cursor(); schema.ensure_tables(c); migrate_v32.apply(c); c.close()

    def tearDown(self):
        conn.configure(backend=None,sqlite_path=None,mysql_config=None)

    def test_doing(self):
        ctx=CommandContext(parts=["doing","写代码"],uid="1",ws=None,is_group=False,gid=0)
        out=asyncio.run(cmd_doing(ctx))
        self.assertIn("记下了",out)
        p=presence.get_presence(str(__import__("bot.core.state",fromlist=["MASTER_QQ"]).MASTER_QQ))
        self.assertEqual(p["source"],"manual")


if __name__=="__main__": unittest.main()
