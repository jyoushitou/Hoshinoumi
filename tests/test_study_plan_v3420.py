# ===================== v34.0.2.0 完成/跳过 =====================
import shutil
import tempfile
import unittest
from pathlib import Path

from bot.infra import conn, schema
from bot.life import study_plan as sp
from scripts import migrate_v32


class TestStatusV3420(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.mkdtemp(); self.addCleanup(shutil.rmtree,self.tmp,True)
        conn.configure(backend="sqlite",sqlite_path=str(Path(self.tmp)/"m.db"))
        c=conn.get_cursor(); schema.ensure_tables(c); migrate_v32.apply(c); c.close()
        sp.save_week("u",{"week_start":"2026-11-16","monday":[{"no":1,"task":"x"}]})

    def tearDown(self):
        conn.configure(backend=None,sqlite_path=None,mysql_config=None)

    def test_done(self):
        c=sp.set_status("u","2026-11-16","monday",1,"done")
        self.assertEqual(c["status"],"done")
        self.assertEqual(sp.load_week("u","2026-11-16")["monday"][0]["status"],"done")

    def test_missing(self):
        self.assertIsNone(sp.set_status("u","2026-11-16","monday",9,"done"))


if __name__=="__main__": unittest.main()
