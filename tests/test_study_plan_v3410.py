# ===================== v34.0.1.0 导入/落库 =====================
import shutil
import tempfile
import unittest
from pathlib import Path

from bot.infra import conn, schema
from bot.life import study_plan as sp
from scripts import migrate_v32


class TestStudyPersistenceV3410(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.mkdtemp(); self.addCleanup(shutil.rmtree,self.tmp,True)
        conn.configure(backend="sqlite",sqlite_path=str(Path(self.tmp)/"m.db"))
        self.c=conn.get_cursor(); schema.ensure_tables(self.c); migrate_v32.apply(self.c); self.c.close()

    def tearDown(self):
        conn.configure(backend=None,sqlite_path=None,mysql_config=None)

    def test_import_load_export(self):
        raw='{"week_start":"2026-11-16","monday":[{"time":"09:00","task":"x"}]}'
        sp.import_text("u", raw)
        got=sp.load_week("u","2026-11-18")
        self.assertEqual(got["week_start"],"2026-11-16")
        self.assertEqual(got["monday"][0]["task"],"x")
        self.assertIn("x", sp.export_text("u","2026-11-16"))

    def test_overwrite_no_duplicate(self):
        sp.save_week("u",{"week_start":"2026-11-16","monday":[]})
        sp.save_week("u",{"week_start":"2026-11-16","monday":[{"task":"y"}]})
        c=conn.get_cursor(); c.execute("SELECT COUNT(*) AS n FROM study_plans")
        self.assertEqual(c.fetchone()["n"],1); c.close()


if __name__=="__main__": unittest.main()
