# ===================== v34.2.1.2 主动消息策略 =====================
import shutil
import tempfile
import unittest
from pathlib import Path

from bot.infra import conn, schema
from bot.life import presence
from scripts import migrate_v32


class TestPolicyV34212(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.mkdtemp(); self.addCleanup(shutil.rmtree,self.tmp,True)
        conn.configure(backend="sqlite",sqlite_path=str(Path(self.tmp)/"m.db"))
        c=conn.get_cursor(); schema.ensure_tables(c); migrate_v32.apply(c); c.close()

    def tearDown(self):
        conn.configure(backend=None,sqlite_path=None,mysql_config=None)

    def test_meeting_blocks(self):
        presence.set_presence("u","meeting")
        self.assertFalse(presence.proactive_allowed("u"))

    def test_coding_allows(self):
        presence.set_presence("u","coding")
        self.assertTrue(presence.proactive_allowed("u"))


if __name__=="__main__": unittest.main()
