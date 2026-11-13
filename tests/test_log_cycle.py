# ===================== v21.5 持久层环 =====================
import unittest
from pathlib import Path


class TestPersistenceCycle(unittest.TestCase):
    def test_settings_does_not_import_log(self):
        p = Path(__file__).resolve().parents[1] / "bot" / "core" / "settings.py"
        text = p.read_text(encoding="utf-8")
        self.assertNotIn("from ..log", text)
        self.assertNotIn("import log_api", text)

    def test_log_does_not_import_db(self):
        p = Path(__file__).resolve().parents[1] / "bot" / "log.py"
        text = p.read_text(encoding="utf-8")
        self.assertNotIn("from .infra import conn", text)
        self.assertNotIn("from .infra import db", text)
        self.assertNotIn("get_cursor", text)

    def test_settings_import_clean(self):
        import importlib
        import bot.core.settings as settings

        importlib.reload(settings)
        self.assertTrue(hasattr(settings, "load"))


if __name__ == "__main__":
    unittest.main()
