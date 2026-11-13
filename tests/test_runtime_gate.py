# ===================== v19.0 run.py 启动门禁 =====================
import unittest

import run as R


class TestRuntimeGate(unittest.TestCase):
    def setUp(self):
        from botv.core import features
        from botv.app import runtime_checks

        self.f = features
        self.rc = runtime_checks
        self._orig = (features.load, features.read_report,
                      runtime_checks.check_network, runtime_checks.check_persona)

    def tearDown(self):
        self.f.load, self.f.read_report, self.rc.check_network, self.rc.check_persona = self._orig

    def test_missing_report_blocks(self):
        self.f.load = lambda: {"features": {"chat": {"enabled": True, "required": True}},
                               "environment": {}}
        self.f.read_report = lambda data: (False, "missing", None)
        self.assertFalse(R._runtime_gate())

    def test_required_unavailable_blocks(self):
        self.f.load = lambda: {"features": {"chat": {"enabled": True, "required": True}},
                               "environment": {}}
        self.f.read_report = lambda data: (
            True, "ok", {"features": {"chat": {"available": False, "reason": "db"}}})
        self.assertFalse(R._runtime_gate())

    def test_ok_passes(self):
        self.f.load = lambda: {"features": {"chat": {"enabled": True, "required": True}},
                               "environment": {"network_required": True}}
        self.f.read_report = lambda data: (
            True, "ok", {"features": {"chat": {"available": True}}})
        self.rc.check_network = lambda: "net ok"
        self.rc.check_persona = lambda: "persona ok"
        self.assertTrue(R._runtime_gate())


if __name__ == "__main__":
    unittest.main()
