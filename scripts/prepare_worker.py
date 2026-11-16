#!/usr/bin/env python3
# ===================== 准备 worker 版本目录（v25.5.3） =====================
# 把源码复制到 data/workers/versions/<version>/，再把运行时共享项软链过去。
# 这样 supervisor 的 cwd=version_dir 才真的加载新代码。

import argparse
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {".git", ".venv", ".tmp", "release", "data", "logs", "__pycache__",
        ".pytest_cache", "APK", "ingress_test", "node_modules"}
SHARE = (".env", "config.local.json", "gateway.env", "data", "logs", "personas")


def copy_tree(src: Path, dst: Path):
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    for item in src.iterdir():
        if item.name in SKIP or item.name.startswith(".test-"):
            continue
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"))
        else:
            shutil.copy2(item, target)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--source", default=str(ROOT))
    ap.add_argument("--base", default=str(ROOT / "data" / "workers"))
    args = ap.parse_args()
    src = Path(args.source).resolve()
    dst = Path(args.base) / "versions" / args.version
    print(f"[prepare] {src} -> {dst}")
    (ROOT / "logs").mkdir(exist_ok=True)
    copy_tree(src, dst)
    for name in SHARE:
        s = ROOT / name
        if not s.exists():
            continue
        d = dst / name
        if d.exists() or d.is_symlink():
            if d.is_dir() and not d.is_symlink():
                shutil.rmtree(d)
            else:
                d.unlink()
        try:
            os.symlink(s, d)
        except OSError:
            if s.is_dir():
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)
    # v28.4：把启用插件快照和 registry generation 写进版本目录
    try:
        from bot.core import settings
        from bot.infra import conn
        from bot.plugins.store import PluginStore
        from bot.plugins.lock import write_lock

        backend = settings.storage_backend()
        conn.configure(
            mysql_config=settings.db_config() if backend == "mysql" else None,
            backend=backend,
            sqlite_path=settings.sqlite_path() if backend == "sqlite" else None,
        )
        store = PluginStore()
        write_lock(dst, store.generation(), store.list(enabled_only=True))
        print("[prepare] plugin-lock.json 已写入")
    except Exception as e:
        print(f"[prepare] plugin-lock 跳过：{e}")

    # 版本文件必须存在
    ver = dst / "bot" / "core" / "version.py"
    if not ver.exists():
        print("[prepare] 失败：源码不完整，缺 bot/core/version.py")
        return 1
    print("[prepare] OK；worker 将从该目录启动")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
