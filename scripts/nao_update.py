#!/usr/bin/env python3
# ===================== 自动热更新入口（v25.4） =====================
# 只接受 release/versions/<version>/ 下、带 update.json 且不要求重启/迁移的版本。
# 需要迁移或重启：拒绝、保留 current、写状态文件。

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bot.core import update_guard  # noqa: E402


def current_schema():
    from bot.core import settings

    backend = settings.storage_backend()
    if backend == "sqlite":
        try:
            conn = sqlite3.connect(settings.sqlite_path())
            row = conn.execute("SELECT v FROM bot_meta WHERE k='schema_version'").fetchone()
            conn.close()
            return str(row[0]) if row else ""
        except Exception:
            return ""
    try:
        import pymysql
        cfg = settings.db_config()
        conn = pymysql.connect(host=cfg["host"], port=cfg["port"], user=cfg["user"],
                               password=cfg["password"], database=cfg["database"],
                               charset="utf8mb4", connect_timeout=3)
        with conn.cursor() as c:
            c.execute("SELECT v FROM bot_meta WHERE k='schema_version'")
            row = c.fetchone()
        conn.close()
        return str(row[0]) if row else ""
    except Exception:
        return ""


def version_key(name):
    parts = []
    for p in str(name).replace("v", "").split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def latest_candidate(base: Path):
    versions = base / "versions"
    items = [p for p in versions.iterdir() if p.is_dir() and (p / "update.json").exists()] if versions.exists() else []
    return sorted(items, key=lambda p: version_key(p.name))[-1] if items else None


def write_status(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=str(ROOT / "release"))
    ap.add_argument("--candidate", default="")
    ap.add_argument("--latest", action="store_true")
    ap.add_argument("--worker-cmd", default=f"{sys.executable} -u nao_run.py")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    base = Path(args.base)
    cand = latest_candidate(base) if args.latest else (Path(args.candidate) if args.candidate else None)
    status_path = ROOT / "data" / "update_status.json"
    if not cand or not cand.exists():
        print("[update] 没有候选版本")
        return 2
    manifest, err = update_guard.read_manifest(cand / "update.json")
    schema = current_schema()
    allowed, reason = update_guard.check(manifest or {}, schema)
    text = update_guard.status_text(manifest or {}, allowed, reason or err)
    print(text)
    write_status(status_path, {
        "version": (manifest or {}).get("version", cand.name),
        "path": str(cand), "schema": schema,
        "allowed": allowed, "reason": reason or err,
        "at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
    })
    if not allowed:
        return 2
    if args.dry_run:
        return 0
    cmd = [sys.executable, str(ROOT / "scripts" / "nao_supervisor.py"),
           "--base", str(ROOT / "data" / "workers"),
           "--version", str(manifest["version"]),
           "--worker-cmd", args.worker_cmd]
    rc = subprocess.call(cmd, cwd=str(ROOT))
    if rc == 0:
        write_status(status_path, {
            "version": manifest["version"], "path": str(cand), "schema": schema,
            "allowed": True, "reason": "switched",
            "at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        })
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
