#!/usr/bin/env python3
# ===================== nao-ingress（v25.2） =====================
# 对外持有 3001/27004；worker 通过 Unix socket 接流量。
# 用法：
#   NAO_WORKER_SOCKET_DIR=/run/nao/worker python3 -m bot.ingress
#   NAO_WORKER_SOCKET_DIR=... NAO_WORKER_MODE=1 python3 run.py

import argparse
import asyncio
import os
import signal

import websockets

from .core import worker

HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
       "te", "trailers", "transfer-encoding", "upgrade", "host", "content-length"}


def _headers(request):
    return {k: v for k, v in request.headers.items() if k.lower() not in HOP}


async def _http_proxy(request):
    from aiohttp import ClientSession, UnixConnector, web
    body = await request.read()
    url = f"http://worker{request.path_qs}"
    try:
        connector = UnixConnector(path=worker.active_socket("api.sock"))
        async with ClientSession(connector=connector) as session:
            async with session.request(request.method, url, headers=_headers(request),
                                       data=body) as resp:
                data = await resp.read()
                headers = {k: v for k, v in resp.headers.items() if k.lower() not in HOP}
                return web.Response(status=resp.status, headers=headers, body=data)
    except Exception as e:
        return web.json_response({"ok": False, "error": f"worker unavailable: {e}"}, status=502)


async def _ws_copy(src, dst):
    try:
        async for msg in src:
            await dst.send(msg)
    except Exception:
        pass
    finally:
        try:
            await dst.close()
        except Exception:
            pass


async def _ws_proxy(client):
    path = worker.active_socket("qq.sock")
    try:
        async with websockets.unix_connect(path) as upstream:
            await asyncio.gather(_ws_copy(client, upstream), _ws_copy(upstream, client))
    except Exception:
        try:
            await client.close(code=1011, reason="worker unavailable")
        except Exception:
            pass


async def main_async(args):
    from aiohttp import web
    worker.set_directory(args.worker_dir)
    app = web.Application()
    app.router.add_route("*", "/{tail:.*}", lambda r: _http_proxy(r))
    runner = web.AppRunner(app, handle_signals=False)
    await runner.setup()
    site = web.TCPSite(runner, args.host, args.http_port, reuse_address=True, reuse_port=True)
    await site.start()

    ws = await websockets.serve(_ws_proxy, args.host, args.ws_port,
                                ping_interval=20, ping_timeout=60)
    print(f"[ingress] HTTP :{args.http_port} WS :{args.ws_port} -> {args.worker_dir}")
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            pass
    try:
        await stop.wait()
    finally:
        ws.close()
        await ws.wait_closed()
        await runner.cleanup()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker-dir", default=os.getenv("NAO_WORKER_SOCKET_DIR", "data/worker"))
    ap.add_argument("--host", default=os.getenv("NAO_LISTEN_HOST", "0.0.0.0"))
    ap.add_argument("--http-port", type=int, default=int(os.getenv("NAO_API_PORT", "27004")))
    ap.add_argument("--ws-port", type=int, default=int(os.getenv("NAO_WS_PORT", "3001")))
    args = ap.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
