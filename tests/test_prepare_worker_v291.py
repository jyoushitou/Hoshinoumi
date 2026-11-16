# ===================== v28.9.1 prepare 保护运行中版本 =====================
import os
import tempfile
import unittest
from pathlib import Path

from scripts.prepare_worker import live_pid


class TestPrepareGuard(unittest.TestCase):
    def test_live_pid_detected(self):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(d, ignore_errors=True))
        (d / "worker.pid").write_text(str(os.getpid()), encoding="utf-8")
        self.assertEqual(live_pid(d), os.getpid())

    def test_dead_pid_ignored(self):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(d, ignore_errors=True))
        (d / "worker.pid").write_text("999999", encoding="utf-8")
        self.assertIsNone(live_pid(d))


if __name__ == "__main__":
    unittest.main()
