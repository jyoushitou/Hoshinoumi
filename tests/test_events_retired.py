# ===================== v21.4 events 视图退场 =====================
import unittest
from pathlib import Path


class TestEventsRetired(unittest.TestCase):
    def test_no_from_events_in_runtime(self):
        root = Path(__file__).resolve().parents[1] / "bot"
        bad = []
        for p in root.rglob("*.py"):
            text = p.read_text(encoding="utf-8", errors="ignore")
            if "FROM events" in text or "JOIN events" in text:
                bad.append(str(p.relative_to(root)))
        self.assertEqual(bad, [], f"仍有运行代码读 events: {bad}")

    def test_schema_has_no_events_view(self):
        from bot.infra import schema

        self.assertNotIn("events", schema.VIEWS)

    def test_migrate_drops_compat_view(self):
        text = (Path(__file__).resolve().parents[1] / "scripts" / "migrate.py").read_text(
            encoding="utf-8")
        self.assertIn("DROP VIEW IF EXISTS events", text)


if __name__ == "__main__":
    unittest.main()
