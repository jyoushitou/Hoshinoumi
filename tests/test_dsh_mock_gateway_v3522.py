# ===================== v35.2.16.0 DSH mock gateway =====================
import json
import threading
import unittest
import urllib.error
import urllib.request

import importlib.util
from pathlib import Path


def load_mock_gateway():
    path = Path(__file__).resolve().parents[1] / "integrations" / "dsh-plugin" / "mock_gateway.py"
    spec = importlib.util.spec_from_file_location("hoshinoumi_mock_gateway", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class MockGatewayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_mock_gateway()
        cls.server = cls.mod.serve(port=0, host="127.0.0.1", token="mock-token")
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def get(self, path, token=False):
        req = urllib.request.Request(self.base + path)
        if token:
            req.add_header("Authorization", "Bearer mock-token")
        with urllib.request.urlopen(req, timeout=3) as r:
            return r.status, json.loads(r.read().decode("utf-8"))

    def post(self, path, body, token=True):
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(self.base + path, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        if token:
            req.add_header("Authorization", "Bearer mock-token")
        with urllib.request.urlopen(req, timeout=3) as r:
            return r.status, json.loads(r.read().decode("utf-8"))

    def test_health_ready(self):
        self.assertEqual(self.get("/healthz")[0], 200)
        status, data = self.get("/readyz")
        self.assertEqual(status, 200)
        self.assertEqual(data["schema"], 34)

    def test_status_requires_token(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.get("/api/status")
        self.assertEqual(ctx.exception.code, 401)
        status, data = self.get("/api/status", token=True)
        self.assertEqual(status, 200)
        self.assertEqual(data["master_qq"], "822891053")

    def test_memory_and_history(self):
        _, mem = self.get("/api/memory", token=True)
        self.assertEqual(mem["total_targets"], 2)
        _, hist = self.get("/internal/history?target_id=822891053&limit=10")
        self.assertGreaterEqual(len(hist["data"]), 1)

    def test_chat_and_command(self):
        status, data = self.post("/api/chat", {"message": "存钱", "target_id": "822891053"})
        self.assertEqual(status, 200)
        self.assertIn("3,300", data["reply"])
        status, data = self.post("/api/command", {"command": "status"})
        self.assertEqual(status, 200)
        self.assertIn("schema", data["result"])

    def test_new_plugin_endpoints(self):
        _, persona = self.get("/api/persona", token=True)
        self.assertTrue(persona["data"])
        _, savings = self.get("/api/savings", token=True)
        self.assertIn("total_cents", savings)
        _, balance = self.get("/api/balance", token=True)
        self.assertTrue(balance["ok"])
        status, weekly = self.post("/api/weekly-plan", {"week": 3, "courses": [{"name": "测试课", "weekday": 1, "period_start": 1}]})
        self.assertEqual(status, 200)
        _, loaded = self.get("/api/weekly-plan?week=3", token=True)
        self.assertEqual(loaded["count"], 1)

    def test_cron_and_logs(self):
        _, cron = self.get("/internal/cron")
        self.assertTrue(cron["data"])
        _, logs = self.get("/api/logs?limit=3", token=True)
        self.assertEqual(len(logs["logs"]), 3)


if __name__ == "__main__":
    unittest.main()
