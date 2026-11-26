# ===================== 文件库（v35.9.28） =====================
# 单层文件库：分片上传 / 列表 / 下载分片 / 删除 / 分享。
# 文件落在 data/files/，数据库 shared_files 只存元数据。
from __future__ import annotations

import base64
import hashlib
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from ..infra import tenant
from .common import json_response

ROOT = Path(__file__).resolve().parents[2]
FILES_ROOT = ROOT / "data" / "files"
MAX_FILE = 30 * 1024 * 1024
CHUNK = 4 * 1024 * 1024
QUOTA = 2 * 1024 * 1024 * 1024
SAFE_NAME = re.compile(r"[^\w\u4e00-\u9fff.\-()\s]+")


def _uid(request):
    return tenant.owner_id()


def _clean_name(raw):
    name = SAFE_NAME.sub("_", Path(str(raw or "")).name).strip(" .")
    return (name or "file")[:120]


def _cursor():
    from ..infra.conn import get_cursor
    return get_cursor()


def _row(r):
    return {k: r[k] for k in ("id", "name", "mime", "size", "sha256", "created_at", "downloads", "max_downloads", "share_token", "share_expires_at") if k in r}


def _share_url(token):
    return "/api/files/share/" + token


def _used(uid):
    c = _cursor()
    try:
        c.execute("SELECT COALESCE(SUM(size),0) AS total FROM shared_files WHERE user_id=%s", (uid,))
        row = c.fetchone()
        return int((row or {}).get("total", 0) or 0)
    finally:
        try: c.close()
        except Exception: pass


async def handle_files(request):
    uid = _uid(request)
    c = _cursor()
    try:
        c.execute("SELECT id,name,mime,size,sha256,created_at,downloads,max_downloads,share_token,share_expires_at "
                  "FROM shared_files WHERE user_id=%s ORDER BY created_at DESC", (uid,))
        rows = [_row(r) for r in (c.fetchall() or [])]
        for row in rows:
            if row.get("share_token"):
                row["share_url"] = _share_url(row["share_token"])
        return json_response({"ok": True, "data": rows, "used": _used(uid), "quota": QUOTA})
    finally:
        try: c.close()
        except Exception: pass


async def handle_init(request):
    uid = _uid(request)
    try:
        body = await request.json()
    except Exception:
        return json_response({"ok": False, "error": "invalid_json"}, 400)
    name = _clean_name(body.get("name"))
    try:
        size = int(body.get("size") or 0)
    except (TypeError, ValueError):
        size = 0
    if size <= 0 or size > MAX_FILE:
        return json_response({"ok": False, "error": "bad_size", "message": "单文件最大 30 MB"}, 400)
    if _used(uid) + size > QUOTA:
        return json_response({"ok": False, "error": "quota_exceeded"}, 413)
    file_id = uuid.uuid4().hex
    FILES_ROOT.mkdir(parents=True, exist_ok=True)
    (FILES_ROOT / (file_id + ".part")).write_bytes(b"")
    c = _cursor()
    try:
        c.execute("INSERT INTO shared_files(id,user_id,name,mime,size,sha256,path,created_at,downloads,max_downloads) "
                  "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,0,0)",
                  (file_id, uid, name, str(body.get("mime") or "application/octet-stream")[:100], size, "",
                   "data/files/" + file_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        c.connection.commit()
    finally:
        try: c.close()
        except Exception: pass
    return json_response({"ok": True, "id": file_id, "chunk_size": CHUNK, "size": size})


async def handle_chunk(request):
    uid = _uid(request)
    file_id = str(request.match_info.get("id") or "")
    if not re.fullmatch(r"[a-f0-9]{32}", file_id):
        return json_response({"ok": False, "error": "bad_id"}, 400)
    c = _cursor()
    try:
        c.execute("SELECT id,user_id,size FROM shared_files WHERE id=%s AND user_id=%s", (file_id, uid))
        row = c.fetchone()
    finally:
        try: c.close()
        except Exception: pass
    if not row:
        return json_response({"ok": False, "error": "not_found"}, 404)
    try:
        body = await request.json()
        offset = int(body.get("offset") or 0)
        raw = base64.b64decode(str(body.get("data_base64") or ""), validate=True)
    except Exception:
        return json_response({"ok": False, "error": "bad_chunk"}, 400)
    if len(raw) > CHUNK:
        return json_response({"ok": False, "error": "chunk_too_large"}, 413)
    if offset < 0 or offset + len(raw) > int(row.get("size") or 0):
        return json_response({"ok": False, "error": "bad_offset"}, 400)
    part = FILES_ROOT / (file_id + ".part")
    part.parent.mkdir(parents=True, exist_ok=True)
    with part.open("r+b" if part.exists() else "wb") as handle:
        handle.seek(offset)
        handle.write(raw)
    return json_response({"ok": True, "id": file_id, "offset": offset, "length": len(raw)})


async def handle_complete(request):
    uid = _uid(request)
    file_id = str(request.match_info.get("id") or "")
    if not re.fullmatch(r"[a-f0-9]{32}", file_id):
        return json_response({"ok": False, "error": "bad_id"}, 400)
    c = _cursor()
    try:
        c.execute("SELECT id,user_id,name,mime,size FROM shared_files WHERE id=%s AND user_id=%s", (file_id, uid))
        row = c.fetchone()
    finally:
        try: c.close()
        except Exception: pass
    if not row:
        return json_response({"ok": False, "error": "not_found"}, 404)
    part = FILES_ROOT / (file_id + ".part")
    if not part.exists():
        return json_response({"ok": False, "error": "chunk_missing"}, 400)
    if part.stat().st_size != int(row.get("size") or 0):
        return json_response({"ok": False, "error": "size_mismatch", "expected": row.get("size"), "actual": part.stat().st_size}, 400)
    digest = hashlib.sha256(part.read_bytes()).hexdigest()
    final = FILES_ROOT / file_id
    os.replace(part, final)
    c = _cursor()
    try:
        c.execute("UPDATE shared_files SET sha256=%s,path=%s WHERE id=%s AND user_id=%s",
                  (digest, "data/files/" + file_id, file_id, uid))
        c.connection.commit()
    finally:
        try: c.close()
        except Exception: pass
    return json_response({"ok": True, "id": file_id, "sha256": digest, "size": row.get("size")})


async def handle_download(request):
    uid = _uid(request)
    file_id = str(request.match_info.get("id") or "")
    return _download(request, owner=uid, file_id=file_id)


def _download(request, owner=None, file_id="", token=""):
    c = _cursor()
    try:
        if token:
            c.execute("SELECT id,name,mime,size,path,share_expires_at,downloads,max_downloads FROM shared_files WHERE share_token=%s", (token,))
        else:
            c.execute("SELECT id,name,mime,size,path FROM shared_files WHERE id=%s AND user_id=%s", (file_id, owner))
        row = c.fetchone()
        if not row:
            return json_response({"ok": False, "error": "not_found"}, 404)
        if token and row.get("share_expires_at"):
            try:
                if datetime.strptime(str(row["share_expires_at"])[:19], "%Y-%m-%d %H:%M:%S") < datetime.now():
                    return json_response({"ok": False, "error": "share_expired"}, 410)
            except Exception:
                pass
        if token and int(row.get("max_downloads") or 0) and int(row.get("downloads") or 0) >= int(row.get("max_downloads") or 0):
            return json_response({"ok": False, "error": "download_limit"}, 410)
        try:
            offset = max(0, int(request.query.get("offset", 0)))
            length = min(CHUNK, max(1, int(request.query.get("length", CHUNK))))
        except (TypeError, ValueError):
            return json_response({"ok": False, "error": "bad_range"}, 400)
        path = ROOT / str(row.get("path") or "")
        if not path.exists():
            return json_response({"ok": False, "error": "file_missing"}, 404)
        size = int(row.get("size") or path.stat().st_size)
        if token and offset == 0:
            c.execute("UPDATE shared_files SET downloads=downloads+1 WHERE share_token=%s", (token,))
            c.connection.commit()
        with path.open("rb") as handle:
            handle.seek(offset)
            raw = handle.read(length)
        return json_response({"ok": True, "id": row["id"], "name": row["name"], "mime": row["mime"],
                              "size": size, "offset": offset, "length": len(raw),
                              "data_base64": base64.b64encode(raw).decode()})
    finally:
        try: c.close()
        except Exception: pass


async def handle_share_download(request):
    return _download(request, token=str(request.match_info.get("token") or ""))


async def handle_delete(request):
    uid = _uid(request)
    file_id = str(request.match_info.get("id") or "")
    c = _cursor()
    try:
        c.execute("SELECT path FROM shared_files WHERE id=%s AND user_id=%s", (file_id, uid))
        row = c.fetchone()
        if not row:
            return json_response({"ok": False, "error": "not_found"}, 404)
        c.execute("DELETE FROM shared_files WHERE id=%s AND user_id=%s", (file_id, uid))
        c.connection.commit()
    finally:
        try: c.close()
        except Exception: pass
    for suffix in ("", ".part"):
        try:
            (FILES_ROOT / (file_id + suffix)).unlink(missing_ok=True)
        except Exception:
            pass
    return json_response({"ok": True, "id": file_id})


async def handle_share_create(request):
    uid = _uid(request)
    file_id = str(request.match_info.get("id") or "")
    try:
        body = await request.json()
    except Exception:
        body = {}
    hours = max(1, min(24 * 30, int(body.get("expires_hours") or 24)))
    max_downloads = max(0, min(10000, int(body.get("max_downloads") or 0)))
    token = secrets.token_urlsafe(18)
    expires = (datetime.now() + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    c = _cursor()
    try:
        c.execute("UPDATE shared_files SET share_token=%s,share_expires_at=%s,downloads=0,max_downloads=%s "
                  "WHERE id=%s AND user_id=%s", (token, expires, max_downloads, file_id, uid))
        if c.rowcount <= 0:
            return json_response({"ok": False, "error": "not_found"}, 404)
        c.connection.commit()
    finally:
        try: c.close()
        except Exception: pass
    return json_response({"ok": True, "token": token, "url": _share_url(token), "expires_at": expires, "max_downloads": max_downloads})


async def handle_share_info(request):
    token = str(request.match_info.get("token") or "")
    c = _cursor()
    try:
        c.execute("SELECT id,name,mime,size,created_at,share_expires_at,downloads,max_downloads FROM shared_files WHERE share_token=%s", (token,))
        row = c.fetchone()
        if not row:
            return json_response({"ok": False, "error": "not_found"}, 404)
        return json_response({"ok": True, "data": {**_row(row), "expires_at": row.get("share_expires_at")}})
    finally:
        try: c.close()
        except Exception: pass
