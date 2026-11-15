# ===================== v25.0 配置中心 =====================
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class TestAppConfig(unittest.TestCase):
    def setUp(self):
        from bot.core import appconfig
        self.A = appconfig
        self.tmp = tempfile.TemporaryDirectory()
        self.orig_file = appconfig.CONFIG_FILE
        appconfig.CONFIG_FILE = str(Path(self.tmp.name) / "config.local.json")
        self.A.reload()

    def tearDown(self):
        self.A.CONFIG_FILE = self.orig_file
        self.A.reload()
        self.tmp.cleanup()

    def test_defaults(self):
        self.assertEqual(self.A.get("memory.max_user_round"), 50)
        self.assertEqual(self.A.get("summary.max_tokens"), 1024)
        self.assertEqual(self.A.get("reading.chunk_chars"), 1000)
        self.assertEqual(self.A.source("memory.max_user_round"), "default")

    def test_file_and_invalid(self):
        Path(self.A.CONFIG_FILE).write_text(json.dumps({
            "app": {"memory.max_user_round": 60, "summary.max_tokens": 99999}
        }), encoding="utf-8")
        self.A.reload()
        self.assertEqual(self.A.get("memory.max_user_round"), 60)
        self.assertEqual(self.A.source("memory.max_user_round"), "config")
        self.assertEqual(self.A.get("summary.max_tokens"), 1024)

    def test_env_overrides_file_then_invalid_falls_back(self):
        Path(self.A.CONFIG_FILE).write_text(json.dumps({
            "app": {"memory.max_user_round": 60}
        }), encoding="utf-8")
        with mock.patch.dict("os.environ", {"NAO_MAX_USER_ROUND": "70"}):
            self.A.reload()
            self.assertEqual(self.A.get("memory.max_user_round"), 70)
            self.assertEqual(self.A.source("memory.max_user_round"), "env")
        with mock.patch.dict("os.environ", {"NAO_MAX_USER_ROUND": "bad"}):
            self.A.reload()
            self.assertEqual(self.A.get("memory.max_user_round"), 60)

    def test_runtime_and_reload(self):
        ok, _ = self.A.set_runtime("memory.max_user_round", "80")
        self.assertTrue(ok)
        self.assertEqual(self.A.get("memory.max_user_round"), 80)
        self.assertEqual(self.A.source("memory.max_user_round"), "runtime")
        self.A.reload()
        self.assertEqual(self.A.get("memory.max_user_round"), 50)

    def test_range_rejected(self):
        ok, _ = self.A.set_runtime("memory.max_user_round", "9999")
        self.assertFalse(ok)
        self.assertEqual(self.A.get("memory.max_user_round"), 50)


if __name__ == "__main__":
    unittest.main()
