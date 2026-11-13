# ===================== v21.6 AI/life/schedule 环 =====================
import asyncio
import unittest
from pathlib import Path


class TestAiPort(unittest.TestCase):
    def test_diary_uses_port(self):
        p = Path(__file__).resolve().parents[1] / "bot" / "diary" / "generate.py"
        text = p.read_text(encoding="utf-8")
        self.assertNotIn("from ..ai.client", text)
        self.assertIn("ai_port.generate_text", text)

    def test_schedule_runner_does_not_import_ai_or_diary(self):
        p = Path(__file__).resolve().parents[1] / "bot" / "schedule" / "runner.py"
        text = p.read_text(encoding="utf-8")
        self.assertNotIn("from ..ai.client", text)
        self.assertNotIn("from ..diary", text)

    def test_port_roundtrip(self):
        from bot.core import ai_port

        async def fake(messages, max_tokens=0, target_id=None):
            return "ok"

        ai_port.register_text(fake)
        out = asyncio.run(ai_port.generate_text([{"role": "user", "content": "x"}]))
        self.assertEqual(out, "ok")


if __name__ == "__main__":
    unittest.main()
