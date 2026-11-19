# ===================== 人设卡 API（v35.2.18.0） =====================
# 只读 personas/<name>/，给 DSH 插件展示真实人设卡。
# 不返回完整 prompt 给非 owner；DSH 的 API token 本身是 owner。
from pathlib import Path

from ..ai import persona_loader
from .common import json_response

ROOT = Path(__file__).resolve().parents[2]
CARD_ROOT = ROOT / "personas"
TEXT_FILES = ("prompt.txt", "supplement.txt", "life.txt")
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
