# ===================== 插件管理 API（v35.9.4.2 真实后端） =====================
# 真实插件目录 / plugin_registry + 安装待审批 sidecar。
from __future__ import annotations

import json
import shutil
import tempfile
import threading
import urllib.request
import zipfile
from pathlib import Path

from ..plugins import loader
from ..plugins.store import PluginStore
from .common import json_response

ROOT = Path(__file__).resolve().parents[2]
PENDING_FILE = ROOT / "data" / "plugins" / "pending.json"
_LOCK = threading.Lock()


def _load_pending():
    try:
        data = json.loads(PENDING_FILE.read_text(encoding="utf-8"))
        return [x for x in data if isinstance(x, dict) and x.get("name")] if isinstance(data, list) else []
    except Exception:
        return []


def _save_pending(rows):
    PENDING_FILE.parent.mkdir(parents=True, exist_ok=True)
    PENDING_FILE.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _pending_item(name, rec=None, permissions=None):
    return {
        "name": name,
        "version": getattr(rec, "version", "0.1.0") if rec else "0.1.0",
        "permissions": list(permissions or (getattr(rec, "capabilities", ()) if rec else [])),
        "description": "待 owner 审批",
        "path": getattr(rec, "path", "") if rec else "",
    }


def _row(rec, pending=False):
    return {
        "id": rec.name if hasattr(rec, "name") else rec["name"],
        "name": rec.name if hasattr(rec, "name") else rec["name"],
        "slug": rec.name if hasattr(rec, "name") else rec["name"],
        "enabled": False if pending else bool(getattr(rec, "enabled", False)),
        "pending": pending,
        "permissions": list(getattr(rec, "capabilities", ()) or rec.get("permissions") or []),
        "version": getattr(rec, "version", "0.1.0") if hasattr(rec, "version") else rec.get("version", "0.1.0"),
        "description": getattr(rec, "layer", "") if hasattr(rec, "layer") else rec.get("description", "待审批"),
    }


def _extract(raw):
    tmp = Path(tempfile.mkdtemp(prefix=".plugin-", dir=ROOT / "data"))
    try:
        with zipfile.ZipFile(raw) as archive:
            names = archive.namelist()
            if len(names) > 500:
                raise ValueError("文件数量超过限制")
            for name in names:
                if name.startswith("/") or ".." in Path(name).parts or "\\" in name:
                    raise ValueError("非法包路径：" + name)
            archive.extractall(tmp)
        return tmp
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise


async def handle_list(request):
    store = PluginStore()
    pending = _load_pending()
    pending_names = {x["name"] for x in pending}
    rows = [_row(rec) for rec in store.list() if rec.name not in pending_names]
    rows += [_row({**x, "permissions": x.get("permissions") or []}, pending=True) for x in pending]
    installed = len([x for x in rows if not x["pending"]])
    return json_response({
        "ok": True,
        "data": rows,
        "stats": {"installed": installed, "pending": len(pending), "errors": 0},
        "permissions": [],
        "errors": [],
    })


async def handle_install(request):
    try:
        body = await request.json()
    except Exception:
        return json_response({"ok": False, "error": "invalid_json"}, 400)
    raw = None
    tmp = None
    try:
        if body.get("source") == "url":
            url = str(body.get("url") or "").strip()
            if not url.startswith(("http://", "https://")):
                return json_response({"ok": False, "error": "bad_url"}, 400)
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "HoshinoumiPlugin/1"}), timeout=15) as response:
                raw = response.read(20 * 1024 * 1024 + 1)
            if len(raw) > 20 * 1024 * 1024:
                return json_response({"ok": False, "error": "package_too_large"}, 413)
        elif body.get("package_base64"):
            import base64
            raw = base64.b64decode(str(body["package_base64"]), validate=True)
            if len(raw) > 20 * 1024 * 1024:
                return json_response({"ok": False, "error": "package_too_large"}, 413)
        else:
            return json_response({"ok": False, "error": "unsupported_source", "message": "真实后端只支持 .zip/.plugin 包上传"}, 400)
        tmp = _extract(__import__("io").BytesIO(raw))
        manifest = loader.read_manifest(tmp)
        rec = loader.install_package(tmp)
        store = PluginStore()
        store.set_enabled(rec.name, False)
        with _LOCK:
            pending = [x for x in _load_pending() if x.get("name") != rec.name]
            pending.append(_pending_item(rec.name, rec))
            _save_pending(pending)
        return json_response({"ok": True, "data": _row(rec, pending=True), "source": "package"})
    except Exception as exc:
        return json_response({"ok": False, "error": "install_failed", "message": str(exc)}, 400)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


async def handle_toggle(request):
    name = request.match_info.get("id", "")
    store = PluginStore()
    rec = store.get(name)
    if not rec:
        return json_response({"ok": False, "error": "plugin_not_found"}, 404)
    if any(x.get("name") == name for x in _load_pending()):
        return json_response({"ok": False, "error": "pending_approval"}, 409)
    store.set_enabled(name, not bool(rec.enabled))
    return json_response({"ok": True, "data": _row(store.get(name))})


async def handle_approve(request):
    name = request.match_info.get("id", "")
    with _LOCK:
        pending = _load_pending()
        item = next((x for x in pending if x.get("name") == name), None)
        if not item:
            return json_response({"ok": False, "error": "not_pending"}, 409)
        PluginStore().set_enabled(name, True)
        _save_pending([x for x in pending if x.get("name") != name])
    return json_response({"ok": True, "data": _row(PluginStore().get(name))})


async def handle_reject(request):
    name = request.match_info.get("id", "")
    with _LOCK:
        pending = _load_pending()
        item = next((x for x in pending if x.get("name") == name), None)
        if not item:
            return json_response({"ok": False, "error": "not_pending"}, 409)
        rec = PluginStore().get(name)
        path = str(getattr(rec, "path", "") or item.get("path") or "")
        try:
            from ..infra.conn import get_cursor
            c = get_cursor(); c.execute("DELETE FROM plugin_registry WHERE name=%s", (name,)); c.connection.commit(); c.close()
        except Exception:
            pass
        if path and (ROOT / path).exists():
            shutil.rmtree(ROOT / path, ignore_errors=True)
        _save_pending([x for x in pending if x.get("name") != name])
    return json_response({"ok": True, "deleted": name})
