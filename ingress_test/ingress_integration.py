import asyncio
import subprocess
import sys
import time
from pathlib import Path

import aiohttp
import websockets


async def wait_http(port):
    for _ in range(60):
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(f"http://127.0.0.1:{port}/api/health", timeout=1) as r:
                    if r.status == 200:
                        return await r.json()
        except Exception:
            pass
        await asyncio.sleep(0.25)
    raise RuntimeError("http not ready")


async def main():
    d = "/tmp/fake-worker"
    Path(d).mkdir(parents=True, exist_ok=True)
    w = subprocess.Popen([sys.executable, "fake_unix_worker.py", d], stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True)
    line = w.stdout.readline()
    print("worker:", line.strip())
    ing = subprocess.Popen([sys.executable, "-m", "bot.ingress", "--worker-dir", d,
                            "--host", "127.0.0.1", "--http-port", "18004", "--ws-port", "18001"],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        print("health:", await wait_http(18004))
        async with aiohttp.ClientSession() as s:
            async with s.post("http://127.0.0.1:18004/echo", data="hello") as r:
                print("post:", r.status, await r.json())
        async with websockets.connect("ws://127.0.0.1:18001") as c:
            await c.send("ws-hello")
            print("ws:", await asyncio.wait_for(c.recv(), 3))
    finally:
        ing.terminate()
        w.terminate()
        try:
            ing.wait(timeout=5)
        except Exception:
            ing.kill()
        try:
            w.wait(timeout=5)
        except Exception:
            w.kill()


asyncio.run(main())
