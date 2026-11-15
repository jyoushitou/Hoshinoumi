# ===================== v25.5.8 supervisor 诊断 =====================
import asyncio
import tempfile
import unittest
from pathlib import Path


class TestSupervisorDiagnostics(unittest.TestCase):
    def test_worker_exit_code(self):
        from scripts.nao_supervisor import wait_health

        class P:
            returncode = 7

            def poll(self):
                return 7

        ok, why = asyncio.run(wait_health("/tmp/no.sock", P(), timeout=0.1))
        self.assertFalse(ok)
        self.assertIn("code=7", why)

    def test_log_tail(self):
        from scripts.nao_supervisor import _tail
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "worker.log"
            p.write_text("a\nb\nc\n", encoding="utf-8")
            self.assertEqual(_tail(p, 2), "b\nc")
            self.assertEqual(_tail(Path(d) / "missing.log", 2).startswith("(读取失败"), True)


if __name__ == "__main__":
    unittest.main()
