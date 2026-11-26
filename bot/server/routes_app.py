# ===================== 客户端更新 / 下载（v35.9.31） =====================
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .common import json_response

ROOT = Path(__file__).resolve().parents[2]
APK_DIR = ROOT / "data" / "apk"


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
    if platform not in ("android", "all"):
        return json_response({"ok": False, "error": "platform_not_found"}, 404)
    return json_response({"ok": True, "data": manifest})
