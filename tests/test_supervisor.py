# ===================== v25.5 current 指针 =====================
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class TestCurrentPointer(unittest.TestCase):
    def test_text_pointer_fallback(self):
        from scripts.nao_supervisor import switch_current
        from bot.core import worker

        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            target = base / "versions" / "25.5.0"
            target.mkdir(parents=True)
            (target / "api.sock").write_text("x")
            with mock.patch("os.symlink", side_effect=OSError("no symlink")):
                switch_current(base, target)
            old = os.environ.get("NAO_WORKER_SOCKET_DIR")
            os.environ["NAO_WORKER_SOCKET_DIR"] = str(base)
            try:
                p = worker.active_socket("api.sock")
                self.assertIn("25.5.0", p)
                self.assertTrue(p.endswith("api.sock"))
            finally:
                if old is None:
                    os.environ.pop("NAO_WORKER_SOCKET_DIR", None)
                else:
                    os.environ["NAO_WORKER_SOCKET_DIR"] = old


if __name__ == "__main__":
    unittest.main()


