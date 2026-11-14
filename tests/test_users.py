# ===================== v23.0 账号底座 =====================
import shutil
import tempfile
import unittest
from pathlib import Path


class TestUsersBase(unittest.TestCase):
    def setUp(self):
        from bot.infra import conn, schema, repo_users
        self.tmp = tempfile.mkdtemp()
        self.path = str(Path(self.tmp) / "users.db")
        conn.configure(backend="sqlite", sqlite_path=self.path)
        self.c = conn.get_cursor()
        schema.ensure_tables(self.c)
        repo_users.ensure_defaults(self.c)
        self.R = repo_users

    def tearDown(self):
        try:
            self.c.close()
        except Exception:
            pass
        from bot.infra import conn
        conn.configure(backend=None, sqlite_path=None, mysql_config=None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_owner_and_roles(self):
        owner = self.R.get("__owner__")
        self.assertIsNotNone(owner)
        self.assertEqual(owner["role"], "owner")
        roles = self.R.list_users()
        self.assertTrue(any(r["id"] == "__owner__" for r in roles))

    def test_create_bind_and_resolve(self):
        self.R.create("u_a", "A", role="user")
        self.assertTrue(self.R.bind_identity("u_a", "web", "a@example.com"))
        self.assertEqual(self.R.resolve_identity("web", "a@example.com"), "u_a")
        self.assertTrue(self.R.set_status("u_a", "banned"))
        self.assertEqual(self.R.get("u_a")["status"], "banned")
        self.assertTrue(self.R.set_role("u_a", "admin"))
        self.assertEqual(self.R.get("u_a")["role"], "admin")

    def test_identity_unique(self):
        self.R.create("u_a")
        self.R.create("u_b")
        self.R.bind_identity("u_a", "qq", "10001")
        self.R.bind_identity("u_b", "qq", "10001")
        self.assertEqual(self.R.resolve_identity("qq", "10001"), "u_a")


if __name__ == "__main__":
    unittest.main()
