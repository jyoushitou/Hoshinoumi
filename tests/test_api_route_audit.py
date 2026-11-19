# ===================== 前端接口与后端路由对账 =====================
# 防止前端/插件调用不存在的后端路由；只做静态文本检查，不启动服务。

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_PY = ROOT / "bot" / "server" / "http_api.py"


def backend_routes():
    text = API_PY.read_text(encoding="utf-8")
    paths = re.findall(r'add_(?:get|post|put|patch|delete)\("([^"]+)"', text)
    return {p.split("?")[0] for p in paths}


def frontend_calls():
    paths = set()
    for f in (ROOT / "integrations" / "web" / "src").rglob("*"):
        if f.suffix not in (".ts", ".vue"):
            continue
        text = f.read_text(encoding="utf-8")
        for raw in re.findall(r"http\.(?:get|post)\([^\n]*?['\"]([^'\"]+)", text):
            paths.add(raw.split("?")[0])
    return paths


def plugin_targets():
    paths = set()
    vscode = (ROOT / "integrations" / "vscode-plugin" / "extension.js").read_text(encoding="utf-8")
    for raw in re.findall(r"'\/[a-z][^']*': '([^']+)'", vscode):
        if raw.startswith(("/api/", "/internal/", "/healthz", "/readyz")):
            paths.add(raw.split("?")[0])
    dsh = (ROOT / "integrations" / "dsh-plugin" / "index.js").read_text(encoding="utf-8")
    for raw in re.findall(r"backendFetch\([^,]+,\s*[`\"']([^`\"']+)", dsh):
        if raw.startswith(("/api/", "/internal/", "/healthz", "/readyz")):
            paths.add(raw.split("?")[0])
    return paths


def matches(route, path):
    pattern = re.sub(r"\{[^}]+\}", "[^/]+", re.escape(route))
    return re.fullmatch(pattern, path) is not None


class ApiRouteAuditTests(unittest.TestCase):
    def test_web_calls_have_routes(self):
        routes = backend_routes()
        for path in frontend_calls():
            self.assertTrue(any(matches(r, path) for r in routes), f"Web 调用无后端路由: {path}")

    def test_plugin_targets_have_routes(self):
        routes = backend_routes()
        for path in plugin_targets():
            self.assertTrue(any(matches(r, path) for r in routes), f"插件目标无后端路由: {path}")

    def test_vscode_history_uses_public_history(self):
        text = (ROOT / "integrations" / "vscode-plugin" / "extension.js").read_text(encoding="utf-8")
        self.assertIn("'/history': '/api/history'", text)


if __name__ == "__main__":
    unittest.main()
