# ===================== v28.5 审批 / 错误 / 自动停用 =====================
import asyncio
import json
import shutil
import tempfile
import unittest
from unittest import mock
from pathlib import Path
from types import SimpleNamespace

from bot.cmd.registry import CommandContext
from bot.cmd.plugin_cmd import cmd_plugin
from bot.plugins.loader import install_package
from bot.plugins.store import PluginStore
from scripts import migrate_v28


def make_pkg(root):
    p = Path(root)
    p.mkdir(parents=True)
    (p / "plugin.json").write_text(json.dumps({
        "name": "demo", "author": "a", "layer": "tools", "version": "1.0.0",
        "api_version": 1, "requires_core": ">=28.0.0",
        "capabilities": ["tool.demo@1"], "entrypoint": "plugin:factory",
        "auto_start": True,
    }), encoding="utf-8")
    (p / "plugin.py").write_text("def factory(ctx):\n    return {}\n", encoding="utf-8")
    return p


def ctx(*args):
    return CommandContext(parts=["plugin", *args], uid="1", ws=None,
                          is_group=False, gid=0)


class TestPluginAdmin(unittest.TestCase):
    def setUp(self):
        from bot.infra import conn, schema
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        conn.configure(backend="sqlite", sqlite_path=str(Path(self.tmp) / "p.db"))
        self.c = conn.get_cursor()
        schema.ensure_tables(self.c)
        self.c.connection.commit()
        migrate_v28.apply(self.c)
        self.store = PluginStore()
        self.plugins = Path(self.tmp) / "plugins"
        self.pkg = make_pkg(Path(self.tmp) / "pkg")
        self._patch = mock.patch("bot.plugins.loader.PLUGINS", self.plugins)
        self._patch.start()
        self.addCleanup(self._patch.stop)

    def tearDown(self):
        try:
            self.c.close()
        except Exception:
            pass
        from bot.infra import conn
        conn.configure(backend=None, sqlite_path=None, mysql_config=None)

    def test_install_pending_approve_and_list(self):
        out = asyncio.run(cmd_plugin(ctx("install", str(self.pkg))))
        self.assertIn("等待审批", out)
        self.assertIn("demo", asyncio.run(cmd_plugin(ctx("pending"))))
        self.assertIn("demo", asyncio.run(cmd_plugin(ctx("approve", "1"))))
        listing = asyncio.run(cmd_plugin(ctx("list")))
        self.assertIn("demo", listing)
        self.assertNotIn("core", listing.lower())

    def test_permission_command(self):
        install_package(self.pkg, store=self.store, plugins_dir=self.plugins)
        out = asyncio.run(cmd_plugin(
            ctx("permission", "demo", "db.read", "2", "plugin_demo_x")))
        self.assertIn("= 2", out)
        from bot.plugins.permissions import PermissionStore
        self.assertTrue(PermissionStore("demo").require("db.read", "plugin_demo_x"))

    def test_errors_auto_disable(self):
        install_package(self.pkg, store=self.store, plugins_dir=self.plugins)
        self.store.set_enabled("demo", True)
        for i in range(5):
            self.store.record_error("demo", "E", f"boom{i}")
        self.assertFalse(self.store.get("demo").enabled)
        self.assertTrue(self.store.errors("demo"))


if __name__ == "__main__":
    unittest.main()
