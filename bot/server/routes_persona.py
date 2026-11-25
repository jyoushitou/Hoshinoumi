# ===================== 人设卡 API（v35.2.18.0） =====================
# 只读 personas/<name>/，给 DSH 插件展示真实人设卡。
# 不返回完整 prompt 给非 owner；DSH 的 API token 本身是 owner。
from pathlib import Path
import base64
import io
import json
import os
import shutil
import tempfile
import zipfile
from aiohttp import web

from ..ai import persona_loader
from .common import json_response

ROOT = Path(__file__).resolve().parents[2]
CARD_ROOT = ROOT / "personas"
TEXT_FILES = ("prompt.txt", "supplement.txt", "life.txt")
MAX_TEXT = 100_000
MAX_JSON = 20_000
JSON_FILES = ("state.json", "voice.json")


def _safe_name(name: str) -> str:
    name = (name or "").strip()
    if not name or "/" in name or "\\" in name or name.startswith("."):
        return ""
    return name


def _read_text(path: Path, limit=4000):
    try:
        text = path.read_text(encoding="utf-8").strip()
    except Exception:
        return None
    return text[:limit] if limit else text


def _read_json(path: Path):
    try:
        import json
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, (dict, list)) else None
    except Exception:
        return None


def _summary(name: str, full=False):
    d = CARD_ROOT / name
    if not d.is_dir():
        return None
    prompt = _read_text(d / "prompt.txt", 160) or ""
    item = {
        "name": name,
        "display": _read_text(d / "display.txt", 80) or name,
        "active": persona_loader.active_name() == name,
        "files": {
            "prompt": (d / "prompt.txt").is_file(),
            "life": (d / "life.txt").is_file(),
            "supplement": (d / "supplement.txt").is_file(),
            "state": (d / "state.json").is_file(),
            "voice": (d / "voice.json").is_file(),
        },
        "prompt_excerpt": prompt,
        "state": _read_json(d / "state.json"),
        "voice": _read_json(d / "voice.json"),
    }
    if full:
        item["prompt"] = _read_text(d / "prompt.txt", 0)
        item["supplement"] = _read_text(d / "supplement.txt", 0)
        item["life"] = _read_text(d / "life.txt", 0)
    return item


def cards(full=False):
    out = []
    if CARD_ROOT.is_dir():
        for d in sorted(CARD_ROOT.iterdir(), key=lambda x: x.name.lower()):
            if d.is_dir() and not d.name.startswith("."):
                item = _summary(d.name, full=full)
                if item:
                    out.append(item)
    return out


async def handle_persona(request):
    full = (request.query.get("full") or "").strip() in ("1", "true", "yes")
    raw_name = request.query.get("name", "")
    name = _safe_name(raw_name)
    if raw_name and not name:
        return json_response({"ok": False, "error": "invalid_persona", "message": "bad name"}, 404)
    if name:
        item = _summary(name, full=full)
        if not item:
            return json_response({"ok": False, "error": "persona_not_found", "message": name}, 404)
        return json_response({"ok": True, "data": item, "active": persona_loader.active_name()})
    data = cards(full=full)
    return json_response({
        "ok": True,
        "data": data,
        "active": persona_loader.active_name(),
        "count": len(data),
    })


async def handle_export(request):
    name = _safe_name(request.query.get("name", ""))
    if not name:
        return json_response({"ok": False, "error": "bad_name"}, 400)
    item = _summary(name, full=True)
    if not item:
        return json_response({"ok": False, "error": "persona_not_found"}, 404)
    if (request.query.get("format") or "package") == "json":
        return json_response({"ok": True, "data": item})
    buffer = io.BytesIO()
    folder = CARD_ROOT / name
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("name.txt", name)
        for filename in ("display.txt", "prompt.txt", "life.txt", "supplement.txt", "state.json", "voice.json"):
            path = folder / filename
            if path.is_file():
                archive.writestr(filename, path.read_bytes())
    payload = buffer.getvalue()
    return web.Response(body=payload, content_type="application/octet-stream", headers={
        "Content-Disposition": f'attachment; filename="{name}.hoshinoumi.persona"',
        "Content-Length": str(len(payload)),
        "Access-Control-Allow-Origin": "*",
    })


async def handle_import(request):
    try:
        body = await request.json()
    except Exception:
        return json_response({"ok": False, "error": "invalid_json"}, 400)
    if not isinstance(body, dict):
        return json_response({"ok": False, "error": "invalid_body"}, 400)
    if body.get("package_base64"):
        try:
            raw = base64.b64decode(str(body.get("package_base64")), validate=True)
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                names = archive.namelist()
                if len(names) > 20 or any(("/" in n or "\\" in n or n.startswith("..")) for n in names):
                    raise ValueError("非法包路径")
                package_name = archive.read("name.txt").decode("utf-8").strip() if "name.txt" in names else ""
                name = _safe_name(str(body.get("name") or package_name))
                if not name or "prompt.txt" not in names:
                    raise ValueError("包缺少 name.txt / prompt.txt")
                def read_text(filename):
                    return archive.read(filename).decode("utf-8") if filename in names else ""
                data = {"name": name, "display": read_text("display.txt").strip(), "prompt": read_text("prompt.txt"), "supplement": read_text("supplement.txt"), "life": read_text("life.txt")}
                for filename, key in (("state.json", "state"), ("voice.json", "voice")):
                    if filename in names:
                        data[key] = json.loads(archive.read(filename).decode("utf-8"))
        except Exception as exc:
            return json_response({"ok": False, "error": "bad_package", "message": str(exc)}, 400)
    else:
        data = body.get("data") if isinstance(body.get("data"), dict) else body
    name = _safe_name(data.get("name", ""))
    if not name:
        return json_response({"ok": False, "error": "bad_name"}, 400)
    prompt = data.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return json_response({"ok": False, "error": "prompt_required"}, 400)
    if len(prompt) > MAX_TEXT:
        return json_response({"ok": False, "error": "prompt_too_large"}, 413)
    target = CARD_ROOT / name
    overwrite = bool(data.get("overwrite"))
    if target.exists() and not overwrite:
        return json_response({"ok": False, "error": "exists", "message": "需要 overwrite=true"}, 409)
    tmp = Path(tempfile.mkdtemp(prefix=".import-", dir=CARD_ROOT))
    backup = None
    try:
        files = {
            "prompt.txt": prompt.strip() + "\n",
            "display.txt": str(data.get("display") or name).strip() + "\n",
            "supplement.txt": str(data.get("supplement") or "").strip() + ("\n" if data.get("supplement") else ""),
            "life.txt": str(data.get("life") or "").strip() + ("\n" if data.get("life") else ""),
        }
        for fn, text in files.items():
            if len(text) > MAX_TEXT:
                raise ValueError(fn + " too large")
            (tmp / fn).write_text(text, encoding="utf-8")
        for fn, key in (("state.json", "state"), ("voice.json", "voice")):
            value = data.get(key)
            if value is not None:
                if not isinstance(value, (dict, list)):
                    raise ValueError(key + " must be object")
                raw = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
                if len(raw) > MAX_JSON:
                    raise ValueError(key + " too large")
                (tmp / fn).write_text(raw, encoding="utf-8")
        if target.exists():
            backup = CARD_ROOT / (".backup-" + name)
            if backup.exists():
                shutil.rmtree(backup)
            os.replace(target, backup)
        os.replace(tmp, target)
        tmp = None
        if backup and backup.exists():
            shutil.rmtree(backup)
        return json_response({"ok": True, "data": _summary(name, full=False)})
    except Exception as e:
        if tmp and tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)
        if backup and backup.exists() and not target.exists():
            os.replace(backup, target)
        return json_response({"ok": False, "error": "import_failed", "message": str(e)}, 400)


async def handle_activate(request):
    try:
        body = await request.json()
    except Exception:
        return json_response({"ok": False, "error": "invalid_json"}, 400)
    name = _safe_name((body or {}).get("name", ""))
    if not name or not (CARD_ROOT / name).is_dir():
        return json_response({"ok": False, "error": "persona_not_found"}, 404)
    from ..core import state as cfg
    from ..ai import prompt as prompt_mod
    cfg.persona_name = name
    persona_loader.save_active(name)
    try:
        prompt_mod.reload_personality_supplement()
    except Exception:
        pass
    return json_response({"ok": True, "active": name})
