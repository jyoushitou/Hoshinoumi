# ===================== worker 版本清理（v25.5.8） =====================
# 只保留 current + 上一个旧版本；正在运行的 worker 目录不删。

import os
import shutil
from pathlib import Path


def version_key(name):
    parts = []
    for p in str(name).replace("v", "").split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def pid_alive(pid):
    # Windows 的 os.kill(pid, 0) 会发 CTRL_C_EVENT，可能打断测试/进程；
    # 这里保守视为存活，避免误删正在用的目录。
    if os.name == "nt":
        return True
    try:
        os.kill(int(pid), 0)
        return True
    except Exception:
        return False


def current_dir(base):
    p = base / "current"
    try:
        t = Path(os.readlink(p)) if p.is_symlink() else Path(p.read_text(encoding="utf-8").strip())
        return t.resolve() if t.is_absolute() else (base / t).resolve()
    except Exception:
        return None


def select_removable(base, keep=2):
    """保留 current + 最近 keep 个；正在运行的 worker.pid 也保护。"""
    versions = base / "versions"
    if not versions.exists():
        return []
    cur = current_dir(base)
    dirs = [p for p in versions.iterdir() if p.is_dir()]
    dirs.sort(key=lambda p: version_key(p.name), reverse=True)
    protected = set()
    if cur:
        protected.add(cur.resolve())
    for p in dirs:
        if len(protected) >= max(1, keep):
            break
        protected.add(p.resolve())
    out = []
    for p in dirs:
        if p.resolve() in protected:
            continue
        pidf = p / "worker.pid"
        try:
            pid = int(pidf.read_text(encoding="utf-8").strip())
            if pid_alive(pid):
                continue
        except Exception:
            pass
        out.append(p)
    return out


def cleanup(base, keep=2):
    """删除超出保留数的版本目录；返回删除数量。"""
    removed = 0
    for p in select_removable(Path(base), keep):
        shutil.rmtree(p, ignore_errors=True)
        removed += 1
    return removed
