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
    base = base.resolve()
    target = target.resolve()
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


async def health_detail(api_sock: str, timeout=1.0):
    """返回 (ok, 原因)；诊断用。"""
    import aiohttp

    try:
        conn = aiohttp.UnixConnector(path=api_sock)
        async with aiohttp.ClientSession(connector=conn) as s:
            async with s.get("http://worker/api/health", timeout=timeout) as r:
                body = (await r.text())[:200]
                if r.status == 200:
                    return True, ""
                return False, f"health HTTP {r.status}: {body}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


async def health(api_sock: str, timeout=1.0):
    ok, _why = await health_detail(api_sock, timeout)
    return ok


async def wait_health(api_sock, proc, timeout=30.0):
    """返回 (ok, 原因)；进程退出/超时/非 200 都给出具体原因。"""
    deadline = time.monotonic() + timeout
    last = ""
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return False, f"worker 进程已退出，code={proc.returncode}"
        ok, why = await health_detail(api_sock)
        if ok:
            return True, ""
        last = why
        await asyncio.sleep(0.5)
    return False, f"{timeout:.0f}s 内 {api_sock} 未就绪；最后一次：{last or '无响应'}"


def _tail(path: Path, n=20):
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(lines[-n:]) if lines else "(空)"
    except Exception as e:
        return f"(读取失败: {e})"


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


async def deploy(base: Path, version: str, cmd, timeout=30.0, drain_seconds=60.0):
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
            if not old_dir.is_absolute():
                old_dir = base / old_dir
        elif current.exists():
            old_dir = Path(current.read_text(encoding="utf-8").strip())
            if not old_dir.is_absolute():
                old_dir = base / old_dir
    except OSError:
        old_dir = None
    log = open(version_dir / "worker.log", "ab")
    proc = subprocess.Popen(cmd, cwd=str(version_dir), env=env, start_new_session=True,
                            stdout=log, stderr=subprocess.STDOUT)
    (version_dir / "worker.pid").write_text(str(proc.pid), encoding="utf-8")
    api_sock = str(version_dir / "api.sock")
    ok, reason = await wait_health(api_sock, proc, timeout)
    if not ok:
        stop(proc)
        print(f"[supervisor] {version} 健康检查失败，拒绝切流")
        print(f"  socket: {api_sock}")
        print(f"  原因: {reason}")
        print("  worker.log 最后 20 行：")
        print(_tail(version_dir / "worker.log", 20))
        print("  处理：先看上面的报错；常见为未 source .env、环境报告过期、"
              "依赖缺失、current/socket 权限。")
        try:
            log.close()
        except Exception:
            pass
        return False
    switch_current(base, version_dir)
    print(f"[supervisor] 已切到 {version}（{version_dir}）")
    if old_dir and old_dir.resolve() != version_dir.resolve():
        if drain_seconds > 0:
            print(f"[supervisor] 旧 worker 继续服务 {drain_seconds:.0f}s，保留在途 WS/HTTP")
            await asyncio.sleep(drain_seconds)
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
    ap.add_argument("--worker-cmd", default=f"{sys.executable} -u run.py")
    ap.add_argument("--timeout", type=float, default=30)
    ap.add_argument("--drain-seconds", type=float, default=60)
    args = ap.parse_args()
    base = Path(args.base)
    cmd = shlex.split(args.worker_cmd)
    ok = asyncio.run(deploy(base, args.version, cmd, args.timeout, args.drain_seconds))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
