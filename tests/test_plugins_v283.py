# ===================== v28.3 PluginContext / 权限 =====================
import asyncio
import shutil
import tempfile
import unittest
from pathlib import Path

from bot.registry import PluginManifest
from bot.plugins import (
    PermissionDenied, PermissionRequired, PermissionStore, PluginContext,
)


def manifest():
    return PluginManifest(
        name="demo", author="a", layer="tools", version="1.0.0",
        api_version=1, requires_core=">=28.0.0",
        capabilities=("tool.demo@1",), entrypoint="plugin:factory",
    )


class TestPermissionStore(unittest.TestCase):
    def setUp(self):
        from bot.infra import conn, schema
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        conn.configure(backend="sqlite", sqlite_path=str(Path(self.tmp) / "p.db"))
        self.c = conn.get_cursor()
        schema.ensure_tables(self.c, names=["plugin_permissions"])
        self.c.connection.commit()

    def tearDown(self):
        try:
            self.c.close()
        except Exception:
            pass
        from bot.infra import conn
        conn.configure(backend=None, sqlite_path=None, mysql_config=None)

    def test_default_requires_approval(self):
        p = PermissionStore("demo")
        with self.assertRaises(PermissionRequired):
            p.require("db.read", "plugin_demo_t")

    def test_deny_and_allow(self):
        p = PermissionStore("demo")
        p.set("db.read", "plugin_demo_t", 0)
        with self.assertRaises(PermissionDenied):
            p.require("db.read", "plugin_demo_t")
        p.set("db.read", "plugin_demo_t", 2)
        self.assertTrue(p.require("db.read", "plugin_demo_t"))


class TestPluginContext(unittest.TestCase):
    def setUp(self):
        from bot.infra import conn, schema
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        conn.configure(backend="sqlite", sqlite_path=str(Path(self.tmp) / "c.db"))
        self.c = conn.get_cursor()
        schema.ensure_tables(self.c, names=["plugin_permissions"])
        self.c.execute("CREATE TABLE plugin_demo_items(id INTEGER PRIMARY KEY, name TEXT)")
        self.c.connection.commit()
        self.ctx = PluginContext(manifest())
        self.ctx.files.root = Path(self.tmp) / "data"

    def tearDown(self):
        try:
            self.c.close()
        except Exception:
            pass
        from bot.infra import conn
        conn.configure(backend=None, sqlite_path=None, mysql_config=None)

    def test_db_table_scope_and_permission(self):
        with self.assertRaises(PermissionRequired):
            self.ctx.db.select("plugin_demo_items")
        self.ctx.permissions.set("db.read", "plugin_demo_items", 2)
        self.ctx.permissions.set("db.write", "plugin_demo_items", 2)
        self.ctx.db.insert("plugin_demo_items", {"name": "x"})
        self.assertEqual(self.ctx.db.select("plugin_demo_items")[0]["name"], "x")
        with self.assertRaises(PermissionDenied):
            self.ctx.db.select("users")

    def test_file_path_escape_and_permission(self):
        with self.assertRaises(PermissionDenied):
            self.ctx.files.read("../../etc/passwd")
        self.ctx.permissions.set("file.write", "a.txt", 2)
        self.ctx.permissions.set("file.read", "a.txt", 2)
        self.ctx.files.write("a.txt", b"hi")
        self.assertEqual(self.ctx.files.read("a.txt"), b"hi")

    def test_tasks_owner(self):
        async def run():
            ev = asyncio.Event()

            async def worker():
                await ev.wait()

            t = self.ctx.tasks.spawn("w", worker())
            self.assertEqual(self.ctx.tasks.active(), 1)
            await self.ctx.tasks.cancel_all()
            self.assertTrue(t.cancelled())
        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
