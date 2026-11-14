# ===================== v23.5.0 owner 迁移 =====================
import shutil
import tempfile
import unittest
from pathlib import Path


class TestOwnerMigration(unittest.TestCase):
    def setUp(self):
        from bot.infra import conn, schema
        self.tmp = tempfile.mkdtemp()
        conn.configure(backend="sqlite", sqlite_path=str(Path(self.tmp) / "m.db"))
        self.c = conn.get_cursor()
        schema.ensure_tables(self.c)
        from scripts import migrate_v23
        migrate_v23.apply(self.c)
        self.c.execute("INSERT INTO users(id,nickname,role) VALUES('__owner__','owner','owner')")
        self.c.execute("INSERT INTO identities(user_id,channel,external_id) "
                       "VALUES('__owner__','qq','822891053')")
        self.c.execute("INSERT INTO memories(user_id,target_id,summary) "
                       "VALUES('__owner__','822891053','旧记忆')")
        self.c.execute("INSERT INTO relation_events(user_id,target_id,delta,reason) "
                       "VALUES('__owner__','822891053',-0.1,'x')")
        self.c.execute("INSERT INTO gateway_log(owner,path,status) "
                       "VALUES('__owner__','/api/state',200)")
        self.c.connection.commit()

    def tearDown(self):
        try:
            self.c.close()
        except Exception:
            pass
        from bot.infra import conn
        conn.configure(backend=None, sqlite_path=None, mysql_config=None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_migrate_owner_to_master(self):
        import bot.config
        from scripts import migrate_v24
        orig = bot.config.MASTER_QQ
        bot.config.MASTER_QQ = 822891053
        try:
            out = migrate_v24.apply(self.c)
        finally:
            bot.config.MASTER_QQ = orig
        self.assertEqual(out["new"], "822891053")
        self.c.execute("SELECT id FROM users WHERE id='822891053'")
        self.assertIsNotNone(self.c.fetchone())
        self.c.execute("SELECT user_id FROM memories WHERE target_id='822891053'")
        self.assertEqual(self.c.fetchone()["user_id"], "822891053")
        self.c.execute("SELECT user_id FROM identities WHERE external_id='822891053'")
        self.assertEqual(self.c.fetchone()["user_id"], "822891053")
        self.c.execute("SELECT owner FROM gateway_log LIMIT 1")
        self.assertEqual(self.c.fetchone()["owner"], "822891053")


if __name__ == "__main__":
    unittest.main()

