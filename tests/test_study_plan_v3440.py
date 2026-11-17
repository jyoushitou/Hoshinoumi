# ===================== v34.0.4.0 周统计 =====================
import shutil
import tempfile
import unittest
from pathlib import Path

from bot.infra import conn, schema
from bot.life import study_plan as sp
from scripts import migrate_v32


class TestStatsV3440(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.mkdtemp(); self.addCleanup(shutil.rmtree,self.tmp,True)
        conn.configure(backend="sqlite",sqlite_path=str(Path(self.tmp)/"m.db"))
        c=conn.get_cursor(); schema.ensure_tables(c); migrate_v32.apply(c); c.close()
        sp.save_week("u",{"week_start":"2026-11-16","monday":[
            {"no":1,"task":"a","status":"done","actual_min":30},
            {"no":2,"task":"b","status":"todo"}]})

    def tearDown(self):
        conn.configure(backend=None,sqlite_path=None,mysql_config=None)

    def test_stats(self):
        s=sp.week_stats("u","2026-11-16")
        self.assertEqual(s["total"],2); self.assertEqual(s["done"],1); self.assertEqual(s["completion"],50.0)


if __name__=="__main__": unittest.main()
