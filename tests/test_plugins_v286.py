# ===================== v28.6 插件 stop 跟随 worker =====================
import asyncio
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from bot.plugins.loader import install_package
from bot.plugins.runtime import PluginRuntime
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
    (p / "plugin.py").write_text(
        "import asyncio\n"
        "def factory(ctx):\n"
        "    ctx.on_stop(lambda: setattr(ctx, 'stopped', True))\n"
        "    async def worker():\n"
        "        await asyncio.sleep(60)\n"
        "    ctx.tasks.spawn('w', worker())\n"
        "    return {}\n",
        encoding="utf-8")
    return p


class TestPluginStop(unittest.TestCase):
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
        self._patch = mock.patch("bot.plugins.loader.PLUGINS", self.plugins)
        self._patch.start()
        self.addCleanup(self._patch.stop)
        install_package(make_pkg(Path(self.tmp) / "pkg"), store=self.store,
                        plugins_dir=self.plugins)
        self.store.set_enabled("demo", True)

    def tearDown(self):
        try:
            self.c.close()
        except Exception:
            pass
        from bot.infra import conn
        conn.configure(backend=None, sqlite_path=None, mysql_config=None)

    def test_load_and_stop(self):
        from bot.registry import PluginRegistry

        async def run():
            rt = PluginRuntime(registry=PluginRegistry(), store=self.store)
            self.assertEqual(rt.load_enabled(), 1)
            self.assertIn("demo", rt.loaded)
            self.assertTrue(rt.registry.by_name("demo"))
            ctx, _ = rt.loaded["demo"]
            self.assertEqual(ctx.tasks.active(), 1)
            await rt.stop_all(timeout=2)
            self.assertFalse(rt.registry.by_name("demo"))
            self.assertEqual(ctx.tasks.active(), 0)
            self.assertTrue(getattr(ctx, "stopped", False))
        asyncio.run(run())

    def test_lock_generation_mismatch_skips_load(self):
        from bot.plugins.lock import write_lock
        from bot.plugins.runtime import PluginRuntime
        from bot.registry import PluginRegistry
        from unittest import mock

        write_lock(self.tmp, self.store.generation() + 1, [])
        with mock.patch("bot.plugins.runtime.Path.cwd", return_value=Path(self.tmp)):
            rt = PluginRuntime(registry=PluginRegistry(), store=self.store)
            self.assertEqual(rt.load_enabled(), 0)


if __name__ == "__main__":
    unittest.main()
