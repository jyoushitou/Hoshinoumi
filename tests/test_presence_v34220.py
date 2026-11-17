# ===================== v34.2.2.0 隐私默认 =====================
import shutil
import tempfile
import unittest
from pathlib import Path

from bot.infra import conn, schema
from bot.life import presence
from scripts import migrate_v32


class TestPrivacyV34220(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.mkdtemp(); self.addCleanup(shutil.rmtree,self.tmp,True)
        conn.configure(backend="sqlite",sqlite_path=str(Path(self.tmp)/"m.db"))
        c=conn.get_cursor(); schema.ensure_tables(c); migrate_v32.apply(c); c.close()

    def tearDown(self):
        conn.configure(backend=None,sqlite_path=None,mysql_config=None)

    def test_reporter_detail_dropped(self):
        presence.set_presence("u","coding","secret title")
        self.assertEqual(presence.get_presence("u")["detail"],"")

    def test_manual_detail_kept(self):
        presence.set_presence("u","coding","写计划",0,source="manual")
        self.assertEqual(presence.get_presence("u")["detail"],"写计划")


if __name__=="__main__": unittest.main()
