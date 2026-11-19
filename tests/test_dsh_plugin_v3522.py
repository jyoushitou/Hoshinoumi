# ===================== v35.2.2.0 DSH 客户端插件 =====================
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "integrations" / "dsh-plugin"


class DshPluginPackageTests(unittest.TestCase):
    def test_package_manifest(self):
        data = json.loads((PLUGIN / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(data["name"], "hoshinoumi-dsh")
        self.assertRegex(data["version"], r"^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$")
        self.assertEqual(data["exports"]["./client"], "./client.js")
        self.assertEqual(data["dsh"]["client"]["platform"], "web")
        self.assertEqual(data["dsh"]["bundle"]["patch"], "./cordis.patch.yml")

    def test_bundle_patch_and_entries(self):
        patch = (PLUGIN / "cordis.patch.yml").read_text(encoding="utf-8")
        self.assertIn("hoshinoumi_dsh", patch)
        self.assertIn("hoshinoumi-dsh", patch)
        client = (PLUGIN / "client.js").read_text(encoding="utf-8")
        self.assertIn("__ModuleLoader__", client)
        self.assertIn("HOSHINOMI_DSH_CLIENT_LOADED", client)
        self.assertIn("id: 'hoshinoumi-dsh'", client)
        self.assertIn("conversation.input.right", client)
        self.assertIn("/api/hoshinoumi/ui", client)
        self.assertIn("nao", client)

    def test_host_routes_and_config(self):
        host = (PLUGIN / "index.js").read_text(encoding="utf-8")
        for route in ("/api/hoshinoumi/health", "/api/hoshinoumi/config",
                      "/api/hoshinoumi/test", "/api/hoshinoumi/chat", "/api/hoshinoumi/history",
                      "/api/hoshinoumi/command", "/api/hoshinoumi/ui", "/api/hoshinoumi/status", "/api/hoshinoumi/persona", "/api/hoshinoumi/memory", "/api/hoshinoumi/logs", "/api/hoshinoumi/plan", "/api/hoshinoumi/cron"):
            self.assertIn(route, host)
        self.assertIn("hoshinoumi.json", host)
        self.assertIn("Bearer", host)
        self.assertIn("base_url", host)

    def test_ui_checks_gateway_and_calls_backend(self):
        ui = (PLUGIN / "ui.html").read_text(encoding="utf-8")
        self.assertIn("loadBackendConfig", ui)
        self.assertIn("openSetup", ui)
        self.assertIn("/api/hoshinoumi/config", ui)
        self.assertIn("/api/hoshinoumi/chat", ui)
        self.assertIn("/api/hoshinoumi/command", ui)
        self.assertIn("target_id", ui)
        self.assertIn("后端地址", ui)

    def test_no_secret_in_ui(self):
        ui = (PLUGIN / "ui.html").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"sk-[A-Za-z0-9]{16,}", ui))
        self.assertNotIn("Authorization: Bearer sk-", ui)


if __name__ == "__main__":
    unittest.main()
