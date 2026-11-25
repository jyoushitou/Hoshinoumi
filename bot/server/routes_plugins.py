# ===================== 插件管理 API（v35.9.4.2 真实后端） =====================
# 双格式：
#   - 核心插件：真实 Python 插件目录 + plugin_registry
#   - Web 插件：.hoshinoumi/.zip（plugin.json: id/name/version/apiVersion/entry/permissions）
# Web 插件安装到 data/plugins/web/<id>/，真实文件存储 + 审批。
from __future__ import annotations

import base64
import io
import json
import shutil
import sys
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
WEB_ROOT = ROOT / "data" / "plugins" / "web"
WEB_REGISTRY = WEB_ROOT / "registry.json"
_LOCK = threading.Lock()


def _load_json(path, fallback):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, type(fallback)) else fallback
    except Exception:
        return fallback


def _save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _load_pending():
    return [x for x in _load_json(PENDING_FILE, []) if isinstance(x, dict) and x.get("name")]


def _save_pending(rows):
    _save_json(PENDING_FILE, rows)


def _load_web():
    return [x for x in _load_json(WEB_REGISTRY, []) if isinstance(x, dict) and x.get("id")]


def _save_web(rows):
    _save_json(WEB_REGISTRY, rows)


def _web_row(item, pending=None):
    return {
        "id": item.get("id"), "name": item.get("name") or item.get("id"), "slug": item.get("id"),
        "enabled": bool(item.get("enabled")), "pending": bool(item.get("pending") if pending is None else pending),
        "permissions": list(item.get("permissions") or []), "version": str(item.get("version") or "0.1.0"),
        "description": str(item.get("description") or "Web 插件"),
    }


def _row(rec, pending=False):
    name = rec.name if hasattr(rec, "name") else rec.get("name")
    return {
        "id": name, "name": name, "slug": name,
        "enabled": False if pending else bool(getattr(rec, "enabled", False)),
        "pending": pending,
        "permissions": list(getattr(rec, "capabilities", ()) or (rec.get("permissions") if isinstance(rec, dict) else []) or []),
        "version": getattr(rec, "version", "0.1.0") if hasattr(rec, "version") else str(rec.get("version") or "0.1.0"),
        "description": getattr(rec, "layer", "") if hasattr(rec, "layer") else str(rec.get("description") or "待审批"),
    }


def _core_pending_item(name, rec=None, permissions=None):
    return {"name": name, "version": getattr(rec, "version", "0.1.0") if rec else "0.1.0",
            "permissions": list(permissions or (getattr(rec, "capabilities", ()) if rec else [])),
            "description": "待 owner 审批", "path": getattr(rec, "path", "") if rec else ""}


def _extract_package(raw):
    tmp = Path(tempfile.mkdtemp(prefix=".plugin-", dir=ROOT / "data"))
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            if len(archive.infolist()) > 500:
                raise ValueError("文件数量超过限制")
            total = 0
            for info in archive.infolist():
                name = info.filename
                if name.startswith("/") or ".." in Path(name).parts or "\\" in name:
                    raise ValueError("非法包路径：" + name)
                total += info.file_size
            if total > 50 * 1024 * 1024:
                raise ValueError("解压体积超过限制")
            archive.extractall(tmp)
        return tmp
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise


def _inspect_web_package(raw):
    sys.path.insert(0, str(ROOT / "scripts"))
    from plugin_package import inspect_package, PluginPackageError
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".hoshinoumi") as handle:
            handle.write(raw)
            tmp = Path(handle.name)
        return inspect_package(tmp)
    finally:
        if tmp and tmp.exists():
            tmp.unlink(missing_ok=True)


def _install_web(raw, manifest):
    plugin_id = str(manifest.get("id") or "").strip()
    if not plugin_id:
        raise ValueError("插件缺少 id")
    with _LOCK:
        registry = _load_web()
        if any(x.get("id") == plugin_id for x in registry):
            raise ValueError("插件已安装：" + plugin_id)
        target = WEB_ROOT / plugin_id
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)
        (target / "package.hoshinoumi").write_bytes(raw)
        (target / "plugin.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        pending = "finance" in (manifest.get("permissions") or [])
        item = {"id": plugin_id, "name": str(manifest.get("name") or plugin_id), "version": str(manifest.get("version") or "0.1.0"),
                "permissions": list(manifest.get("permissions") or ["read-only"]), "description": str(manifest.get("description") or "Web 插件"),
                "enabled": not pending, "pending": pending, "path": str(target.relative_to(ROOT))}
        registry.append(item)
        _save_web(registry)
        return _web_row(item)


async def handle_list(request):
    pending = _load_pending()
    pending_names = {x["name"] for x in pending}
    core_rows = [_row(rec) for rec in PluginStore().list() if rec.name not in pending_names]
    core_rows += [_row({**x}, pending=True) for x in pending]
    web_rows = [_web_row(x) for x in _load_web()]
    rows = core_rows + web_rows
    installed = len([x for x in rows if not x["pending"]])
    errors = []
    return json_response({"ok": True, "data": rows, "stats": {"installed": installed, "pending": len([x for x in rows if x["pending"]]), "errors": len(errors)}, "permissions": [], "errors": errors})


async def handle_install(request):
    try:
        body = await request.json()
    except Exception:
        return json_response({"ok": False, "error": "invalid_json"}, 400)
    raw = None
    try:
        if body.get("source") == "url":
            url = str(body.get("url") or "").strip()
            if not url.startswith(("http://", "https://")):
                return json_response({"ok": False, "error": "bad_url"}, 400)
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "HoshinoumiPlugin/1"}), timeout=15) as response:
                raw = response.read(20 * 1024 * 1024 + 1)
            if len(raw) > 20 * 1024 * 1024:
                return json_response({"ok": False, "error": "package_too_large"}, 413)
        elif body.get("package_base64") or body.get("data_base64"):
            raw = base64.b64decode(str(body.get("package_base64") or body.get("data_base64")), validate=True)
            if len(raw) > 20 * 1024 * 1024:
                return json_response({"ok": False, "error": "package_too_large"}, 413)
        else:
            return json_response({"ok": False, "error": "unsupported_source", "message": "只支持 .hoshinoumi/.zip 包"}, 400)

        # 先按 Web 插件规范解析；不匹配再按核心 Python 插件安装
        try:
            manifest = _inspect_web_package(raw)
            item = _install_web(raw, manifest)
            return json_response({"ok": True, "data": item, "source": "web", "mock": False})
        except Exception as web_exc:
            tmp = _extract_package(raw)
            try:
                manifest = loader.read_manifest(tmp)
                rec = loader.install_package(tmp)
                PluginStore().set_enabled(rec.name, False)
                with _LOCK:
                    pending = [x for x in _load_pending() if x.get("name") != rec.name]
                    pending.append(_core_pending_item(rec.name, rec))
                    _save_pending(pending)
                return json_response({"ok": True, "data": _row(rec, pending=True), "source": "core", "mock": False})
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
    except Exception as exc:
        return json_response({"ok": False, "error": "install_failed", "message": str(exc)}, 400)


def _find_web(plugin_id):
    return next((x for x in _load_web() if x.get("id") == plugin_id), None)


async def handle_toggle(request):
    name = request.match_info.get("id", "")
    web = _find_web(name)
    if web:
        if web.get("pending"):
            return json_response({"ok": False, "error": "pending_approval"}, 409)
        web["enabled"] = not bool(web.get("enabled"))
        registry = _load_web()
        for index, item in enumerate(registry):
            if item.get("id") == name:
                registry[index] = web
        _save_web(registry)
        return json_response({"ok": True, "data": _web_row(web)})
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
    web = _find_web(name)
    if web:
        registry = _load_web()
        for index, item in enumerate(registry):
            if item.get("id") == name:
                item["pending"] = False; item["enabled"] = True; registry[index] = item
        _save_web(registry)
        return json_response({"ok": True, "data": _web_row(next(x for x in registry if x.get("id") == name))})
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
    web = _find_web(name)
    if web:
        target = ROOT / str(web.get("path") or "")
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        _save_web([x for x in _load_web() if x.get("id") != name])
        return json_response({"ok": True, "deleted": name})
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
