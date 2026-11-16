# ===================== v28.2 schema 30 / 插件核心表 =====================
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts import migrate_v28


class TestSchemaV282(unittest.TestCase):
    def setUp(self):
        from bot.infra import conn, schema
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.path = str(Path(self.tmp) / "v282.db")
        conn.configure(backend="sqlite", sqlite_path=self.path)
        self.c = conn.get_cursor()
        base = [n for n in schema.TABLES if not n.startswith("plugin_")]
        schema.ensure_tables(self.c, names=base)
        self.c.connection.commit()

    def tearDown(self):
        try:
            self.c.close()
        except Exception:
            pass
        from bot.infra import conn
        conn.configure(backend=None, sqlite_path=None, mysql_config=None)

    def test_plugin_tables_and_schema30(self):
        made = migrate_v28.apply(self.c)
        self.assertEqual(sorted(made), sorted(migrate_v28.PLUGIN_TABLES))
        self.c.execute("SELECT v FROM bot_meta WHERE k='schema_version'")
        self.assertEqual(self.c.fetchone()["v"], "30")
        self.c.execute("SELECT generation FROM plugin_registry_generation WHERE id=1")
        self.assertEqual(self.c.fetchone()["generation"], 0)

    def test_idempotent(self):
        migrate_v28.apply(self.c)
        made = migrate_v28.apply(self.c)
        self.assertEqual(made, [])
        self.c.execute("SELECT COUNT(*) AS n FROM plugin_registry_generation")
        self.assertEqual(self.c.fetchone()["n"], 1)


if __name__ == "__main__":
    unittest.main()
