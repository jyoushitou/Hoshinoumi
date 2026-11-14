# ===================== v22.1 !gw =====================
import asyncio
import unittest
from unittest.mock import patch


class _Cur:
    def __init__(self, rows):
        self.rows = rows
        self.calls = 0

    def execute(self, sql, params=None):
        self.calls += 1

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return {"n": 2 if self.calls == 2 else 3}


class TestGwCommand(unittest.TestCase):
    def test_formats_recent_and_limits(self):
        from bot.cmd import gw_cmd

        rows = [{
            "owner": "owner", "path": "/api/state", "status": 200,
            "cost_ms": 12, "ip": "127.0.0.1", "created_at": "2026-11-14 09:00:00",
        }]
        cur = _Cur(rows)
        with patch.object(gw_cmd, "get_cursor", return_value=cur):
            out = asyncio.run(gw_cmd.cmd_gw(None))
        self.assertIn("网关观测", out)
        self.assertIn("429 2", out)
        self.assertIn("/api/state", out)


if __name__ == "__main__":
    unittest.main()
