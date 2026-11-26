# ===================== 客户端更新 / 下载（v35.9.31） =====================
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .common import json_response

ROOT = Path(__file__).resolve().parents[2]
APK_DIR = ROOT / "data" / "apk"
DESKTOP_DIST = ROOT / "clients" / "electron" / "dist"


def _apk_manifest():
    meta = {}
    try:
        meta = json.loads((APK_DIR / "latest.json").read_text(encoding="utf-8"))
    except Exception:
        pass
    apk = APK_DIR / "latest.apk"
    if not apk.is_file():
        return None
    raw = apk.read_bytes()
    return {
        "platform": "android",
        "name": "Hoshinoumi Android",
        "version": str(meta.get("versionName") or ""),
        "versionCode": int(meta.get("versionCode") or 0),
        "notes": str(meta.get("notes") or ""),
        "size": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "url": "/downloads/latest.apk",
        "file": "latest.apk",
        "available": True,
    }


async def handle_app_update(request):
    manifest = _apk_manifest()
    if not manifest:
        return json_response({"ok": False, "error": "apk_missing"}, 404)
    platform = str(request.query.get("platform") or "android")
    if platform in ("windows", "win32"):
        desktop = _desktop_manifest()
        if not desktop:
            return json_response({"ok": False, "error": "desktop_missing"}, 404)
        return json_response({"ok": True, "data": desktop})
    if platform not in ("android", "all"):
        return json_response({"ok": False, "error": "platform_not_found"}, 404)
    return json_response({"ok": True, "data": manifest})


def _desktop_manifest():
    candidates = sorted(DESKTOP_DIST.glob("Hoshinoumi-*-win.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        return None
    path = candidates[0]
    raw_hash = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            raw_hash.update(chunk)
    name = path.name
    version = name.replace("Hoshinoumi-", "").replace("-win.zip", "")
    return {
        "platform": "windows",
        "name": "Hoshinoumi Desktop",
        "version": version,
        "versionCode": 0,
        "notes": "Windows 便携包（解压即用）",
        "size": path.stat().st_size,
        "sha256": raw_hash.hexdigest(),
        "url": "/downloads/clients/" + name,
        "file": name,
        "available": True,
    }


async def handle_clients(request):
    clients = []
    apk = _apk_manifest()
    if apk:
        clients.append(apk)
    desktop = _desktop_manifest()
    if desktop:
        clients.append(desktop)
    return json_response({"ok": True, "data": clients})
