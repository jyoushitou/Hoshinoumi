# ===================== v33.3.1.1 存储契约 + native =====================
import asyncio
import shutil
import tempfile
import unittest
from pathlib import Path

from bot.infra import conn
from bot.ports.storage import Repository, StorageBackend
from bot.storage.native import MetaRepository, SQLStorage


class TestStorageV3331(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.mkdtemp(); self.addCleanup(shutil.rmtree,self.tmp,True)
        conn.configure(backend="sqlite",sqlite_path=str(Path(self.tmp)/"m.db"))
        c=conn.get_cursor(); c.execute("CREATE TABLE bot_meta(k TEXT PRIMARY KEY,v TEXT)")
        c.connection.commit(); c.close()

    def tearDown(self):
        conn.configure(backend=None,sqlite_path=None,mysql_config=None)

    def test_protocol(self):
        self.assertIsInstance(SQLStorage(), StorageBackend)
        self.assertIsInstance(MetaRepository(), Repository)

    def test_execute(self):
        s=SQLStorage()
        asyncio.run(s.execute("INSERT INTO bot_meta(k,v) VALUES(%s,%s)",("x","1")))
        rows=asyncio.run(s.execute("SELECT k,v FROM bot_meta"))
        self.assertEqual(rows[0]["k"],"x")


if __name__=="__main__": unittest.main()
