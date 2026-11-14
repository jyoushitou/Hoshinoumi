# ===================== v23.5.3 !adduser =====================
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path


def _stub():
    for name, attrs in (("jieba", {"lcut": lambda s: list(s)}), ("PIL", {"Image": None})):
        try:
            __import__(name)
        except ImportError:
            m = types.ModuleType(name)
            for k, v in attrs.items():
                setattr(m, k, v)
            sys.modules[name] = m


_stub()


class _Ctx:
    args = ["123456"]


class TestAddUser(unittest.TestCase):
    def setUp(self):
        from bot.infra import conn, schema
        self.tmp = tempfile.mkdtemp()
        conn.configure(backend="sqlite", sqlite_path=str(Path(self.tmp) / "u.db"))
        self.c = conn.get_cursor()
        schema.ensure_tables(self.c)
        from scripts import migrate_v23
        migrate_v23.apply(self.c)

    def tearDown(self):
        try:
            self.c.close()
        except Exception:
            pass
        from bot.infra import conn
        conn.configure(backend=None, sqlite_path=None, mysql_config=None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_adduser_and_setup_code(self):
        from bot.cmd.admin import cmd_adduser
        from bot.infra import repo_users
        out = __import__("asyncio").run(cmd_adduser(_Ctx()))
        self.assertIn("setup code", out)
        code = out.split("setup code：", 1)[1].splitlines()[0].strip()
        row = repo_users.get("123456")
        self.assertIsNotNone(row)
        self.assertTrue(repo_users.verify_setup_code("123456", code))
        self.assertFalse(repo_users.verify_login("123456", "abcdefgh")[0])
        user, err = repo_users.verify_login("123456", "abcdefgh", code)
        self.assertIsNone(err)
        self.assertEqual(user["id"], "123456")
        self.assertFalse(repo_users.verify_setup_code("123456", code))


if __name__ == "__main__":
    unittest.main()
