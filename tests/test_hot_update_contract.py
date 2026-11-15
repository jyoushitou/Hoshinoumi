# ===================== v25+ 热更新约束 =====================
# 目标：普通版本只切 worker，ingress/gateway 不动。
# 这些是源码级护栏，防止以后又把 worker 改回直接绑 3001/27004。

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestHotUpdateContract(unittest.TestCase):
    def test_worker_uses_unix_frame_in_worker_mode(self):
        text = (ROOT / "bot/main.py").read_text(encoding="utf-8")
        self.assertIn("worker.enabled()", text)
        self.assertIn("start_unix_frame_server", text)
        # 不能无条件 start_tcp_server
        self.assertIn("else:", text)

    def test_ingress_has_tcp_l4_proxy(self):
        text = (ROOT / "bot/ingress.py").read_text(encoding="utf-8")
        self.assertIn("_tcp_proxy", text)
        self.assertIn("internal.sock", text)
        self.assertIn('default=os.getenv("NAO_INGRESS_PROTOCOL", "tcp")', text)

    def test_supervisor_keeps_version_and_internal_tcp(self):
        text = (ROOT / "scripts/nao_supervisor.py").read_text(encoding="utf-8")
        self.assertIn('env["NAO_WORKER_MODE"] = "1"', text)
        self.assertIn('env["NAO_WORKER_VERSION"] = version', text)
        self.assertIn('env["NAO_INTERNAL_TCP"] = "1"', text)

    def test_supervisor_uses_tcp_health(self):
        text = (ROOT / "scripts/nao_supervisor.py").read_text(encoding="utf-8")
        self.assertIn("tcp_health_detail", text)
        self.assertIn('"internal.sock" if use_tcp', text)

    def test_ingress_resolves_current_per_connection(self):
        text = (ROOT / "bot/ingress.py").read_text(encoding="utf-8")
        self.assertIn('worker.active_socket("internal.sock")', text)
        self.assertIn('worker.active_socket("qq.sock")', text)


if __name__ == "__main__":
    unittest.main()
