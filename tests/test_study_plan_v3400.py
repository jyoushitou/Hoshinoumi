# ===================== v34.0.0.0 study_plans schema 33 =====================
import shutil
import tempfile
import unittest
from pathlib import Path

from bot.infra import conn, schema
from scripts import migrate_v32, migrate_v33, migrate_v34


class TestStudySchemaV3400(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.mkdtemp(); self.addCleanup(shutil.rmtree,self.tmp,True)
        conn.configure(backend="sqlite",sqlite_path=str(Path(self.tmp)/"m.db"))
        self.c=conn.get_cursor(); schema.ensure_tables(self.c); self.c.connection.commit()

    def tearDown(self):
        try: self.c.close()
        except Exception: pass
        conn.configure(backend=None,sqlite_path=None,mysql_config=None)

    def test_tables_and_version(self):
        migrate_v32.apply(self.c)
        migrate_v33.apply(self.c)
        migrate_v34.apply(self.c)
        for t in ("study_plans","owner_presence"):
            self.c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=%s",(t,))
            self.assertTrue(self.c.fetchone())
        self.c.execute("SELECT v FROM bot_meta WHERE k='schema_version'")
        self.assertEqual(self.c.fetchone()["v"],"34")

    def test_unique_week(self):
        migrate_v32.apply(self.c)
        self.c.execute("INSERT INTO study_plans(user_id,week_start) VALUES('u','2026-11-16')")
        with self.assertRaises(Exception):
            self.c.execute("INSERT INTO study_plans(user_id,week_start) VALUES('u','2026-11-16')")
        self.c.connection.rollback()


if __name__=="__main__": unittest.main()
