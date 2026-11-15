# ===================== v25.2 ingress / worker socket =====================
import os
import socket
import tempfile
import unittest


@unittest.skipUnless(hasattr(socket, "AF_UNIX"), "本机不支持 AF_UNIX")
class TestWorkerSocket(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.orig = os.environ.get("NAO_WORKER_SOCKET_DIR")
        self.orig_mode = os.environ.get("NAO_WORKER_MODE")
        os.environ["NAO_WORKER_SOCKET_DIR"] = self.tmp.name
        os.environ["NAO_WORKER_MODE"] = "1"

    def tearDown(self):
        if self.orig is None:
            os.environ.pop("NAO_WORKER_SOCKET_DIR", None)
        else:
            os.environ["NAO_WORKER_SOCKET_DIR"] = self.orig
        if self.orig_mode is None:
            os.environ.pop("NAO_WORKER_MODE", None)
        else:
            os.environ["NAO_WORKER_MODE"] = self.orig_mode
        self.tmp.cleanup()

    def test_paths_and_bind(self):
        from bot.core import worker
        self.assertTrue(worker.enabled())
        p = worker.socket_path("api.sock")
        self.assertIn("api.sock", p)
        path, sock = worker.bind_unix("qq.sock")
        try:
            self.assertTrue(os.path.exists(path))
        finally:
            sock.close()
        # 重新准备会清掉旧 socket
        worker.prepare_socket("qq.sock")
        self.assertFalse(os.path.exists(path))


if __name__ == "__main__":
    unittest.main()
