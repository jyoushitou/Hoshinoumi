# ===================== v29.3 环境门禁 =====================
import unittest

from scripts.env_gate import EnvGateError, check_report


class TestEnvGate(unittest.TestCase):
    def test_missing(self):
        with self.assertRaises(EnvGateError):
            check_report(None, "29.3.0")

    def test_missing_version(self):
        with self.assertRaises(EnvGateError):
            check_report({"ok": True}, "29.3.0")

    def test_version_mismatch(self):
        with self.assertRaises(EnvGateError):
            check_report({"version": "v29.2.0"}, "29.3.0")

    def test_match(self):
        self.assertTrue(check_report({"version": "v29.3.0"}, "29.3.0"))


if __name__ == "__main__":
    unittest.main()
