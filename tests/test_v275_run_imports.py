# ===================== v27.5 延迟日记自检不再依赖 bot.db =====================
import asyncio
import unittest
from pathlib import Path
from unittest import mock


class _Cur:
    def __init__(self):
        self.connection = self

    def execute(self, sql, params=None):
        pass

    def commit(self):
        pass

    def fetchone(self):
        return {"n": 0}


class TestRunDiaryImport(unittest.TestCase):
    def test_no_bot_db_imports(self):
        root = Path(".")
        files = [root / "run.py"] + list((root / "bot").rglob("*.py"))
        for p in files:
            text = p.read_text(encoding="utf-8")
            self.assertNotIn("from bot.db", text, str(p))
            self.assertNotIn("import bot.db", text, str(p))

    def test_check_diary_uses_infra_conn(self):
        import run

        async def fake_gen(tid):
            return [], []

        with mock.patch("bot.infra.conn.get_cursor", return_value=_Cur()), \
             mock.patch("bot.diary.generate_missing_7day_diaries", side_effect=fake_gen), \
             mock.patch("bot.log.log_system") as log:
            asyncio.run(run.check_diary())
        self.assertTrue(log.called)


if __name__ == "__main__":
    unittest.main()
