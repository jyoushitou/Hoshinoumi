# ===================== Web 图片消息存储（v35.5.5） =====================
# 图片落盘到 data/web_images；对话历史只存相对路径。
# 历史接口读取时转成 data URL，避免公开图片路由泄露。

import base64
import json
import mimetypes
import uuid
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / "data" / "web_images"
_MAX = 4 * 1024 * 1024
_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
}


def save(img_bytes: bytes, mime: str = "image/png") -> str:
    """保存图片，返回相对路径；超限/空返回空串。"""
    if not img_bytes or len(img_bytes) > _MAX:
        return ""
    BASE.mkdir(parents=True, exist_ok=True)
    ext = _EXT.get((mime or "").lower(), ".png")
    name = uuid.uuid4().hex + ext
    (BASE / name).write_bytes(img_bytes)
    return "web_images/" + name


def _resolve(rel: str) -> Path | None:
    rel = (rel or "").strip()
    if not rel.startswith("web_images/"):
        return None
    p = (BASE.parent / rel).resolve()
    try:
        p.relative_to(BASE.resolve())
    except ValueError:
        return None
    return p


def to_data_url(rel: str) -> str:
    p = _resolve(rel)
    if p is None or not p.is_file():
        return ""
    forced = {".webm": "audio/webm", ".ogg": "audio/ogg", ".m4a": "audio/mp4", ".wav": "audio/wav"}
    mime = forced.get(p.suffix.lower()) or mimetypes.guess_type(p.name)[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


def attach_media(item: dict) -> dict:
    """把 meta 里的附件路径转成 image_url / audio_url。"""
    meta = item.get("meta")
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except Exception:
            meta = None
    if isinstance(meta, dict):
        rel = str(meta.get("attachment_path") or meta.get("image_path") or "")
        kind = str(meta.get("kind") or ("image" if meta.get("image") else ""))
        if rel:
            url = to_data_url(rel)
            if url:
                item["kind"] = kind or "image"
                if kind == "voice":
                    item["audio_url"] = url
                else:
                    item["image_url"] = url
    return item


def attach_image(item: dict) -> dict:
    """兼容旧调用：等价于 attach_media。"""
    return attach_media(item)
