# ===================== v27.8 worker 日志目录共享 =====================
import unittest

from scripts import prepare_worker


class TestWorkerLogs(unittest.TestCase):
    def test_logs_are_shared(self):
        self.assertIn("logs", prepare_worker.SHARE)

    def test_logs_skipped_from_copy_then_shared(self):
        self.assertIn("logs", prepare_worker.SKIP)


if __name__ == "__main__":
    unittest.main()
