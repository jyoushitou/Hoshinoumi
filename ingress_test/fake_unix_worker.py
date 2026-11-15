import asyncio
import json
import os
import sys

from aiohttp import web
import websockets


async def api(request):
    if request.path == "/api/health":
        return web.json_response({"ok": True, "worker": "fake"})
    body = await request.text()
    return web.json_response({"ok": True, "method": request.method,
                              "path": request.path, "body": body})


async def ws(conn):
    async for msg in conn:
        await conn.send(msg)


async def main():
    d = sys.argv[1] if len(sys.argv) > 1 else os.getenv("NAO_WORKER_SOCKET_DIR", "/tmp/fake-worker")
    os.makedirs(d, exist_ok=True)
    app = web.Application()
    app.router.add_route("*", "/{tail:.*}", api)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.UnixSite(runner, os.path.join(d, "api.sock")).start()
    server = await websockets.unix_serve(ws, os.path.join(d, "qq.sock"))
    print("FAKE_READY", flush=True)
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
