# ===================== v19.0 功能清单 / 环境报告 =====================
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from bot.core import features


def _testdir():
    p = Path(".tmp") / "features_test"
    p.mkdir(parents=True, exist_ok=True)
    return p


class TestFeatures(unittest.TestCase):
    def test_default_manifest(self):
        data = features.load()
        self.assertTrue(features.enabled(data, "chat"))
        self.assertTrue(features.required(data, "chat"))
        self.assertFalse(features.required(data, "vision"))

    def test_missing_file_raises(self):
        with self.assertRaises(features.FeaturesError):
            features.load(Path(".tmp") / "no-such-features.json")

    def test_report_roundtrip_and_expiry(self):
        data = json.loads(json.dumps(features.load()))
        report_path = _testdir() / "roundtrip.json"
        data["environment"]["report"] = str(report_path)
        data["environment"]["max_age_hours"] = 24
        report = {
            "schema_version": 1,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "config_hash": features.config_hash(data),
            "ok": True,
            "checks": {},
            "features": {"chat": {"available": True}},
        }
        features.write_report(data, report)
        ok, reason, _ = features.read_report(data)
        self.assertTrue(ok, reason)

        report["checked_at"] = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        features.write_report(data, report)
        ok, reason, _ = features.read_report(data)
        self.assertFalse(ok)
        self.assertIn("过期", reason)
        report_path.unlink(missing_ok=True)

    def test_bad_hash_rejected(self):
        data = json.loads(json.dumps(features.load()))
        p = _testdir() / "badhash.json"
        data["environment"]["report"] = str(p)
        features.write_report(data, {
            "schema_version": 1,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "config_hash": "sha256:bad",
            "ok": True,
            "features": {},
        })
        ok, reason, _ = features.read_report(data)
        self.assertFalse(ok)
        self.assertIn("过期", reason)
        p.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
