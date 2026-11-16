# ===================== v28.4 安装 / loader / lock =====================
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts import migrate_v28
from bot.plugins.loader import install_package, load_plugin, package_hash
from bot.plugins.store import PluginStore
from bot.plugins.lock import read_lock, verify_generation, write_lock
from bot.registry import PluginRegistry


def make_package(root):
    p = Path(root)
    p.mkdir(parents=True)
    (p / "plugin.json").write_text(json.dumps({
        "name": "demo", "author": "a", "layer": "tools",
        "version": "1.0.0", "api_version": 1,
        "requires_core": ">=28.0.0",
        "capabilities": ["tool.demo@1"],
        "entrypoint": "plugin:factory",
    }), encoding="utf-8")
    (p / "plugin.py").write_text(
        "def factory(ctx):\n    return {'name': ctx.manifest.name}\n",
        encoding="utf-8")
    return p


class TestInstallLoader(unittest.TestCase):
    def setUp(self):
        from bot.infra import conn, schema
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.db = str(Path(self.tmp) / "plug.db")
        conn.configure(backend="sqlite", sqlite_path=self.db)
        self.c = conn.get_cursor()
        schema.ensure_tables(self.c)
        self.c.connection.commit()
        migrate_v28.apply(self.c)
        self.store = PluginStore()
        self.pkg = make_package(Path(self.tmp) / "pkg")
        self.plugins = Path(self.tmp) / "plugins"

    def tearDown(self):
        try:
            self.c.close()
        except Exception:
            pass
        from bot.infra import conn
        conn.configure(backend=None, sqlite_path=None, mysql_config=None)

    def test_install_and_duplicate(self):
        rec = install_package(self.pkg, store=self.store, plugins_dir=self.plugins)
        self.assertEqual(rec.name, "demo")
        self.assertFalse(rec.enabled)
        self.assertEqual(rec.package_hash, package_hash(self.pkg))
        rec2 = install_package(self.pkg, store=self.store, plugins_dir=self.plugins)
        self.assertEqual(rec2.package_hash, rec.package_hash)

    def test_loader_and_generation_lock(self):
        install_package(self.pkg, store=self.store, plugins_dir=self.plugins)
        from bot.plugins.errors import PluginLoadError
        with self.assertRaises(PluginLoadError):
            load_plugin("demo", PluginRegistry(), self.store, self.plugins)
        self.store.set_enabled("demo", True)
        ctx, obj = load_plugin("demo", PluginRegistry(), self.store, self.plugins)
        self.assertEqual(obj["name"], "demo")
        gen = self.store.generation()
        path = write_lock(self.tmp, gen, self.store.list(enabled_only=True))
        lock = read_lock(self.tmp)
        self.assertTrue(verify_generation(lock, gen))
        self.assertFalse(verify_generation(lock, gen + 1))


if __name__ == "__main__":
    unittest.main()
