# ===================== v34.2.1.0 情境注入 =====================
import shutil
import tempfile
import unittest
from pathlib import Path

from bot.infra import conn, schema
from bot.life import presence
from scripts import migrate_v32


class TestInjectV34210(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.mkdtemp(); self.addCleanup(shutil.rmtree,self.tmp,True)
        conn.configure(backend="sqlite",sqlite_path=str(Path(self.tmp)/"m.db"))
        c=conn.get_cursor(); schema.ensure_tables(c); migrate_v32.apply(c); c.close()

    def tearDown(self):
        conn.configure(backend=None,sqlite_path=None,mysql_config=None)

    def test_inject(self):
        presence.set_presence("u","coding")
        out=presence.inject("旧事件","u")
        self.assertIn("写代码",out)
        self.assertIn("旧事件",out)

    def test_no_presence(self):
        self.assertEqual(presence.inject("旧事件","u"),"旧事件")


if __name__=="__main__": unittest.main()
