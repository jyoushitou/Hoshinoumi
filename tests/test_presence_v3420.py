# ===================== v34.2.0.0 情境表/API =====================
import shutil
import tempfile
import unittest
from pathlib import Path

from bot.infra import conn, schema
from bot.life import presence
from scripts import migrate_v32


class TestPresenceV3420(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.mkdtemp(); self.addCleanup(shutil.rmtree,self.tmp,True)
        conn.configure(backend="sqlite",sqlite_path=str(Path(self.tmp)/"m.db"))
        c=conn.get_cursor(); schema.ensure_tables(c); migrate_v32.apply(c); c.close()

    def tearDown(self):
        conn.configure(backend=None,sqlite_path=None,mysql_config=None)

    def test_set_get(self):
        presence.set_presence("u","coding","x")
        p=presence.get_presence("u")
        self.assertEqual(p["activity"],"coding")
        self.assertIn("写代码",presence.prompt_block("u"))

    def test_unknown(self):
        self.assertEqual(presence.get_presence("u"),None)
        self.assertEqual(presence.prompt_block("u"),"")


if __name__=="__main__": unittest.main()
