# ===================== v34.0.1.3 !plan import/export =====================
import asyncio
import shutil
import tempfile
import unittest
from pathlib import Path

from bot.cmd.plan_cmd import cmd_plan
from bot.cmd.registry import CommandContext
from bot.infra import conn, schema
from scripts import migrate_v32


class TestPlanImportV3413(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.mkdtemp(); self.addCleanup(shutil.rmtree,self.tmp,True)
        conn.configure(backend="sqlite",sqlite_path=str(Path(self.tmp)/"m.db"))
        c=conn.get_cursor(); schema.ensure_tables(c); migrate_v32.apply(c); c.close()

    def tearDown(self):
        conn.configure(backend=None,sqlite_path=None,mysql_config=None)

    def test_import_export(self):
        ctx=CommandContext(parts=["plan","import",'{"week_start":"2026-11-16","monday":[{"task":"x"}]}'],uid="u",ws=None,is_group=False,gid=0)
        self.assertIn("已导入",asyncio.run(cmd_plan(ctx)))
        ctx2=CommandContext(parts=["plan","export"],uid="u",ws=None,is_group=False,gid=0)
        self.assertIn('"x"',asyncio.run(cmd_plan(ctx2)))


if __name__=="__main__": unittest.main()
