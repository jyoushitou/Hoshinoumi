#!/usr/bin/env python3
# ===================== 蓝绿 worker supervisor（v25.3） =====================
# ingress 持有 3001/27004；本脚本只管理 worker：
#   新版本 worker -> 健康检查 -> 原子切换 current -> 旧 worker 优雅退出
# 失败不切流，旧 current 保持。

import argparse
import asyncio
import os
import shlex
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def switch_current(base: Path, target: Path):
    base.mkdir(parents=True, exist_ok=True)
    tmp = base / "current.tmp"
    try:
        if tmp.exists() or tmp.is_symlink():
            tmp.unlink()
        os.symlink(str(target), tmp)
        os.replace(tmp, base / "current")
    except OSError:
        # 没有 symlink 权限时退回文本指针；ingress/worker 都支持
        (base / "current").write_text(str(target), encoding="utf-8")


async def health(api_sock: str, timeout=1.0):
    import aiohttp

    try:
        conn = aiohttp.UnixConnector(path=api_sock)
        async with aiohttp.ClientSession(connector=conn) as s:
            async with s.get("http://worker/api/health", timeout=timeout) as r:
                return r.status == 200
    except Exception:
        return False


async def wait_health(api_sock, proc, timeout=30.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return False
        if await health(api_sock):
            return True
        await asyncio.sleep(0.5)
    return False


def stop(proc, timeout=20):
    if proc.poll() is not None:
        return
    try:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=timeout)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


async def deploy(base: Path, version: str, cmd, timeout=30.0):
    version_dir = base / "versions" / version
    version_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["NAO_WORKER_MODE"] = "1"
    env["NAO_WORKER_SOCKET_DIR"] = str(version_dir)
    env["NAO_WORKER_VERSION"] = version
    old_dir = None
    current = base / "current"
    try:
        if current.is_symlink():
            old_dir = Path(os.readlink(current))
        elif current.exists():
            old_dir = Path(current.read_text(encoding="utf-8").strip())
    except OSError:
        old_dir = None
    proc = subprocess.Popen(cmd, cwd=str(ROOT), env=env, start_new_session=True)
    (version_dir / "worker.pid").write_text(str(proc.pid), encoding="utf-8")
    ok = await wait_health(str(version_dir / "api.sock"), proc, timeout)
    if not ok:
        stop(proc)
        print(f"[supervisor] {version} 健康检查失败，拒绝切流")
        return False
    switch_current(base, version_dir)
    print(f"[supervisor] 已切到 {version}（{version_dir}）")
    if old_dir and old_dir.resolve() != version_dir.resolve():
        try:
            old_pid = int((old_dir / "worker.pid").read_text(encoding="utf-8").strip())
            os.kill(old_pid, signal.SIGTERM)
            print(f"[supervisor] 旧 worker {old_pid} 收到 SIGTERM")
        except Exception as e:
            print(f"[supervisor] 旧 worker 停止失败: {e}")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=str(ROOT / "data" / "workers"))
    ap.add_argument("--version", required=True)
    ap.add_argument("--worker-cmd", default=f"{sys.executable} run.py")
    ap.add_argument("--timeout", type=float, default=30)
    args = ap.parse_args()
    base = Path(args.base)
    cmd = shlex.split(args.worker_cmd)
    ok = asyncio.run(deploy(base, args.version, cmd, args.timeout))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
