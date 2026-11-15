# ===================== v25.5.8 worker 版本清理 =====================
import os
import tempfile
import unittest
from pathlib import Path


class TestWorkerGC(unittest.TestCase):
    def test_keep_current_and_recent(self):
        from scripts.nao_gc import select_removable

        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            (base / "versions").mkdir()
            for v in ("25.5.4", "25.5.5", "25.5.6", "25.5.7"):
                (base / "versions" / v).mkdir()
            (base / "current").write_text(str(base / "versions" / "25.5.7"), encoding="utf-8")
            out = select_removable(base, 3)
            names = {p.name for p in out}
            self.assertNotIn("25.5.7", names)
            self.assertNotIn("25.5.6", names)
            self.assertEqual(names, {"25.5.4"})

    def test_live_worker_protected(self):
        from scripts.nao_gc import select_removable

        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            (base / "versions").mkdir()
            for v in ("25.5.4", "25.5.5", "25.5.6"):
                (base / "versions" / v).mkdir()
            (base / "current").write_text(str(base / "versions" / "25.5.6"), encoding="utf-8")
            (base / "versions" / "25.5.4" / "worker.pid").write_text(str(os.getpid()))
            out = select_removable(base, 2)
            self.assertNotIn("25.5.4", {p.name for p in out})


if __name__ == "__main__":
    unittest.main()


