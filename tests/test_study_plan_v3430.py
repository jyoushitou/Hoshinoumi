# ===================== v34.0.3.0 到点扫描 =====================
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from bot.infra import conn, schema
from bot.life import study_plan as sp
from scripts import migrate_v32


class TestDueV3430(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.mkdtemp(); self.addCleanup(shutil.rmtree,self.tmp,True)
        conn.configure(backend="sqlite",sqlite_path=str(Path(self.tmp)/"m.db"))
        c=conn.get_cursor(); schema.ensure_tables(c); migrate_v32.apply(c); c.close()
        sp.save_week("u",{"week_start":"2026-11-16","monday":[{"no":1,"time":"09:00","task":"x"}]})

    def tearDown(self):
        conn.configure(backend=None,sqlite_path=None,mysql_config=None)

    def test_due(self):
        w,d,due=sp.due_items("u",datetime(2026,11,16,9,1))
        self.assertEqual(w,"2026-11-16"); self.assertEqual(d,"monday"); self.assertEqual(len(due),1)

    def test_not_due_yet(self):
        self.assertEqual(sp.due_items("u",datetime(2026,11,16,8,0))[2],[])

    def test_mark(self):
        w,d,due=sp.due_items("u",datetime(2026,11,16,9,1))
        sp.mark_notified("u",w,d,1)
        self.assertEqual(sp.due_items("u",datetime(2026,11,16,9,2))[2],[])


if __name__=="__main__": unittest.main()
