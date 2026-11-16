# ===================== v28.1 repo 池会话 =====================
import shutil
import tempfile
import unittest
from pathlib import Path


class TestRepoPool(unittest.TestCase):
    def setUp(self):
        from bot.infra import conn, repo_pool
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.path = str(Path(self.tmp) / "pool.db")
        conn.configure(backend="sqlite", sqlite_path=self.path)
        self.repo_pool = repo_pool
        repo_pool.disable()

    def tearDown(self):
        from bot.infra import conn
        self.repo_pool.disable()
        conn.configure(backend=None, sqlite_path=None, mysql_config=None)

    def _schema(self):
        from bot.infra import conn, schema
        c = conn.get_cursor()
        schema.ensure_tables(c)
        try:
            c.connection.commit()
        finally:
            c.close()

    def test_pooled_repo_sees_committed_schema(self):
        self._schema()
        self.repo_pool.enable()
        from bot.infra import repo_users
        repo_users.ensure_defaults()
        self.assertIsNotNone(repo_users.get("__owner__"))

    def test_disabled_keeps_legacy_behavior(self):
        self._schema()
        self.repo_pool.disable()
        from bot.infra import repo_users
        repo_users.ensure_defaults()
        self.assertIsNotNone(repo_users.get("__owner__"))


if __name__ == "__main__":
    unittest.main()
