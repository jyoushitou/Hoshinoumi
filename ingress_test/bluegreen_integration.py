import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path

import aiohttp
import websockets


async def get_json(port, path):
    async with aiohttp.ClientSession() as s:
        async with s.get(f"http://127.0.0.1:{port}{path}", timeout=2) as r:
            return r.status, await r.text()


async def wait_http(port):
    for _ in range(80):
        try:
            status, _ = await get_json(port, "/api/health")
            if status == 200:
                return
        except Exception:
            pass
        await asyncio.sleep(0.25)
    raise RuntimeError("ingress not ready")


async def main():
    base = Path("/tmp/workers")
    old = base / "versions" / "25.4.0"
    old.mkdir(parents=True, exist_ok=True)
    current = base / "current"
    if current.exists() or current.is_symlink():
        current.unlink()
    os.symlink(old, current)
    oldp = subprocess.Popen([sys.executable, "fake_unix_worker.py", str(old)],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print("old:", oldp.stdout.readline().strip())
    ing = subprocess.Popen([sys.executable, "-m", "bot.ingress", "--worker-dir", str(base),
                            "--host", "127.0.0.1", "--http-port", "18004", "--ws-port", "18001"],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        await wait_http(18004)
        print("before:", await get_json(18004, "/api/health"))
        old_ws = await websockets.connect("ws://127.0.0.1:18001")
        await old_ws.send("before-switch")
        print("old ws before:", await asyncio.wait_for(old_ws.recv(), 3))
        sup = subprocess.run([sys.executable, "scripts/nao_supervisor.py", "--base", str(base),
                              "--version", "25.5.0", "--drain-seconds", "5", "--worker-cmd",
                              f"{sys.executable} fake_unix_worker.py"],
                             capture_output=True, text=True, timeout=60)
        print("supervisor:", sup.returncode, sup.stdout.strip(), sup.stderr.strip())
        await wait_http(18004)
        print("after:", await get_json(18004, "/api/health"))
        print("current:", os.readlink(current) if current.is_symlink() else current.read_text())
        await old_ws.send("during-drain")
        print("old ws during drain:", await asyncio.wait_for(old_ws.recv(), 3))
        await old_ws.close()
        async with websockets.connect("ws://127.0.0.1:18001") as c:
            await c.send("after-switch")
            print("new ws:", await asyncio.wait_for(c.recv(), 3))
    finally:
        ing.terminate()
        oldp.terminate()
        for p in (ing, oldp):
            try:
                p.wait(timeout=5)
            except Exception:
                p.kill()


asyncio.run(main())
