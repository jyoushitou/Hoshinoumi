# ===================== 自动备份（v18.19） =====================
# MySQL → mysqldump + gzip；SQLite → sqlite3 .backup（单文件）。
# 每月 1 号 04:30 由 ticker 触发；保留最近 6 份。

import gzip
import json
import os
import shutil
import sqlite3
import subprocess
import time
from datetime import datetime

from ..config import CST
from ..log import log_api, log_err

KEEP = 6
_INDEX = ".index.json"


def backup_dir(path=None):
    if path:
        return path
    return os.getenv("NAO_BACKUP_DIR") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "backups")


def _load_index(root):
    try:
        with open(os.path.join(root, _INDEX), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_index(root, items):
    os.makedirs(root, exist_ok=True)
    with open(os.path.join(root, _INDEX), "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def _sqlite_backup(src_path, dest):
    src = sqlite3.connect(src_path)
    try:
        dst = sqlite3.connect(dest)
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def _mysql_backup(dest):
    from .conn import _config
    cfg = _config.get("mysql") or {}
    db = cfg.get("database") or cfg.get("db")
    if not db:
        raise RuntimeError("MySQL 配置缺 database")
    cmd = ["mysqldump", "--single-transaction", "--routines", "--triggers",
           "-h", str(cfg.get("host", "127.0.0.1")),
           "-P", str(cfg.get("port", 3306)),
           "-u", str(cfg.get("user", "root")), db]
    env = dict(os.environ)
    if cfg.get("password"):
        env["MYSQL_PWD"] = str(cfg["password"])
    raw = subprocess.run(cmd, capture_output=True, timeout=1800, env=env)
    if raw.returncode != 0:
        raise RuntimeError(raw.stderr.decode("utf-8", "ignore")[:200] or "mysqldump 失败")
    with gzip.open(dest, "wb") as f:
        f.write(raw.stdout)


def _verify(path, backend):
    size = os.path.getsize(path) if os.path.exists(path) else 0
    if size <= 0:
        return False, 0
    if backend == "sqlite":
        try:
            c = sqlite3.connect(path)
            try:
                n = c.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
            finally:
                c.close()
            return n > 0, n
        except Exception:
            return False, 0
    try:
        import re
        with gzip.open(path, "rb") as f:
            head = f.read(2 * 1024 * 1024).decode("utf-8", "ignore")
        return bool(head), len(re.findall(r"CREATE TABLE", head))
    except Exception:
        return False, 0


def _prune(root, items, keep=KEEP):
    files = [it for it in items if it.get("ok") and os.path.exists(os.path.join(root, it["file"]))]
    files.sort(key=lambda x: x.get("ts", 0), reverse=True)
    drop = files[keep:]
    for it in drop:
        try:
            os.remove(os.path.join(root, it["file"]))
        except Exception:
            pass
    keep_set = {it["file"] for it in files[:keep]}
    return [it for it in items if it.get("file") in keep_set]


def run_backup(sqlite_path=None, backend=None, root=None, now=None):
    """执行一次备份，返回 {ok,file,size,tables,error}"""
    now = now or datetime.now(CST)
    root = backup_dir(root)
    os.makedirs(root, exist_ok=True)
    backend = backend or ("sqlite" if sqlite_path else None)
    if not backend:
        from .conn import _resolve_backend
        backend = _resolve_backend()
    stamp = now.strftime("%Y-%m")
    ext = ".db" if backend == "sqlite" else ".sql.gz"
    name = f"nao-{stamp}{ext}"
    dest = os.path.join(root, name)
    try:
        if backend == "sqlite":
            src_path = sqlite_path
            if not src_path:
                from .conn import _resolve_sqlite_path
                src_path = _resolve_sqlite_path()
            _sqlite_backup(src_path, dest)
        else:
            _mysql_backup(dest)
        ok, tables = _verify(dest, backend)
        item = {"file": name, "size": os.path.getsize(dest), "tables": tables,
                "ok": ok, "ts": time.time(), "backend": backend,
                "at": now.strftime("%Y-%m-%d %H:%M:%S")}
        if not ok:
            item["error"] = "校验失败（空文件或查不到表）"
            log_err(f"[备份] {name} 校验失败")
        items = _load_index(root)
        items = [it for it in items if it.get("file") != name] + [item]
        items = _prune(root, items)
        _save_index(root, items)
        log_api(f"[备份] {name} {item['size']} 字节，{tables} 张表")
        return item
    except Exception as e:
        log_err(f"[备份] 失败：{e}")
        return {"ok": False, "file": name, "size": 0, "tables": 0, "error": str(e)}


def list_backups(root=None):
    root = backup_dir(root)
    items = _load_index(root)
    out = []
    for it in items:
        p = os.path.join(root, it.get("file", ""))
        if os.path.exists(p):
            it = dict(it)
            it["size"] = os.path.getsize(p)
            out.append(it)
    out.sort(key=lambda x: x.get("ts", 0), reverse=True)
    return out


def describe(root=None):
    items = list_backups(root)
    if not items:
        return "💾 备份：还没有（!backup run 立即备一份）"
    total = sum(it.get("size", 0) for it in items)
    lines = [f"💾 备份：{len(items)} 份，共 {total / 1024 / 1024:.1f} MB（保留最近 {KEEP} 份）"]
    for it in items[:6]:
        mark = "✅" if it.get("ok") else "❌"
        lines.append(f"  {mark} {it.get('file')}  {it.get('size', 0) / 1024:.0f} KB  "
                     f"{it.get('tables', 0)} 表")
    return "\n".join(lines)
