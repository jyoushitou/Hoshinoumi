#!/usr/bin/env python3
"""Acceptance test for v35.9.4 plugin API against the mock gateway."""
from __future__ import annotations

import base64
import io
import json
import threading
import urllib.error
import urllib.request
import zipfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

BASE = "http://127.0.0.1:27005"
TOKEN = "mock-token"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


def build_package(path: Path, plugin_id: str, permissions: list[str], entry: str = "index.js") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("plugin.json", json.dumps({
            "id": plugin_id, "name": f"测试 {plugin_id}", "version": "0.1.0",
            "apiVersion": 1, "entry": entry, "permissions": permissions,
            "description": "验收测试",
        }, ensure_ascii=False))
        archive.writestr(entry, "export function activate() {}")
    raw = buffer.getvalue()
    path.write_bytes(raw)
    return raw


def call(path: str, method: str = "GET", body: dict | None = None, token: str = TOKEN):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    request = urllib.request.Request(BASE + path, data=data, method=method, headers={**HEADERS, "Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8") or "{}")


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    status, payload = call("/api/plugins")
    checks.append(("owner list", status == 200 and payload.get("ok") is True, f"{status} installed={payload.get('stats', {}).get('installed')}"))
    checks.append(("owner stats", payload.get("stats", {}).get("pending") == 1, str(payload.get("stats"))))

    status, payload = call("/api/plugins", token="bad-token")
    checks.append(("non-owner rejected", status in (401, 403), f"{status} {payload.get('error')}"))

    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        package = root / "demo.hoshinoumi"
        raw = build_package(package, "accept_pkg", ["read-only"])

        body = {"source": "file", "filename": "demo.hoshinoumi", "data_base64": base64.b64encode(raw).decode("ascii")}
        status, payload = call("/api/plugins/install", "POST", body)
        checks.append(("file import", status == 200 and payload.get("data", {}).get("id") == "accept_pkg", f"{status} {payload.get('data', {}).get('id')}"))
        checks.append(("read-only auto-enabled", payload.get("data", {}).get("enabled") is True, str(payload.get("data", {}).get("enabled"))))

        status, payload = call("/api/plugins/install", "POST", body)
        checks.append(("duplicate rejected", status == 409, f"{status} {payload.get('error')}"))

        status, payload = call("/api/plugins/accept_pkg/toggle", "POST", {})
        checks.append(("toggle", status == 200 and payload.get("data", {}).get("enabled") is False, str(payload.get("data", {}).get("enabled"))))

        finance = root / "finance.hoshinoumi"
        raw_finance = build_package(finance, "accept_finance", ["finance"])
        status, payload = call("/api/plugins/install", "POST", {"source": "file", "filename": "finance.hoshinoumi", "data_base64": base64.b64encode(raw_finance).decode("ascii")})
        checks.append(("finance pending", status == 200 and payload.get("data", {}).get("pending") is True and payload.get("data", {}).get("enabled") is False, f"{status} pending={payload.get('data', {}).get('pending')}"))

        status, payload = call("/api/plugins/accept_finance/approve", "POST", {})
        checks.append(("approve", status == 200 and payload.get("data", {}).get("pending") is False and payload.get("data", {}).get("enabled") is True, str(payload.get("data", {}))))

        reject_pkg = root / "reject.hoshinoumi"
        raw_reject = build_package(reject_pkg, "accept_reject", ["finance"])
        status, payload = call("/api/plugins/install", "POST", {"source": "file", "filename": "reject.hoshinoumi", "data_base64": base64.b64encode(raw_reject).decode("ascii")})
        status, payload = call("/api/plugins/accept_reject/reject", "POST", {})
        checks.append(("reject removes", status == 200 and payload.get("action") == "reject", str(payload.get("action"))))

        status, payload = call("/api/plugins/install", "POST", {"source": "file", "filename": "bad.hoshinoumi", "data_base64": base64.b64encode(b"not a zip").decode("ascii")})
        checks.append(("invalid package rejected", status == 400, f"{status} {payload.get('error')}"))

        # URL import over a local static server
        handler = lambda *args, **kwargs: SimpleHTTPRequestHandler(*args, directory=str(root), **kwargs)
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{server.server_address[1]}/url.hoshinoumi"
        build_package(root / "url.hoshinoumi", "accept_url", ["network"])
        status, payload = call("/api/plugins/install", "POST", {"source": "url", "url": url, "filename": "url.hoshinoumi"})
        checks.append(("url import", status == 200 and payload.get("data", {}).get("id") == "accept_url", f"{status} {payload.get('data', {}).get('id')}"))
        server.shutdown()

        status, payload = call("/api/plugins/install", "POST", {"source": "manifest", "manifest": {"id": "accept_manifest", "name": "清单插件", "version": "0.1.0", "apiVersion": 1, "entry": "index.js", "permissions": ["read-only"]}})
        checks.append(("manifest import", status == 200 and payload.get("data", {}).get("id") == "accept_manifest", f"{status} {payload.get('data', {}).get('id')}"))

    for name, ok, detail in checks:
        print(("PASS" if ok else "FAIL"), name, detail)
    failed = [name for name, ok, _ in checks if not ok]
    print(f"\n{len(checks) - len(failed)}/{len(checks)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
