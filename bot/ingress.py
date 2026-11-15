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
        q = ""
        try:
            q = client.request.path
        except Exception:
            pass
        async with websockets.unix_connect(path, uri=f"ws://localhost{q}") as upstream:
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
    site = web.TCPSite(runner, args.http_host, args.http_port)
    await site.start()

    ws = await websockets.serve(_ws_proxy, args.ws_host, args.ws_port,
                                ping_interval=20, ping_timeout=60)
    print(f"[ingress] HTTP {args.http_host}:{args.http_port} WS {args.ws_host}:{args.ws_port} -> {args.worker_dir}")
    stop = asyncio.Event()
    stopping = {"v": False}
    loop = asyncio.get_running_loop()

    def _on_signal():
        # 第一次请求优雅退出；第二次强制退出，避免被活跃 WS 卡死
        if stopping["v"]:
            os._exit(0)
        stopping["v"] = True
        stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _on_signal)
        except (NotImplementedError, RuntimeError):
            pass
    try:
        await stop.wait()
    finally:
        async def _shutdown():
            try:
                ws.close(close_connections=True)
            except TypeError:
                ws.close()
            except Exception:
                pass
            try:
                await asyncio.wait_for(ws.wait_closed(), 3)
            except Exception:
                pass
            try:
                await asyncio.wait_for(runner.cleanup(), 3)
            except Exception:
                pass

        try:
            await asyncio.wait_for(_shutdown(), 8)
        except Exception:
            print("[ingress] 优雅退出超时，强制结束")
            os._exit(0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker-dir", default=os.getenv("NAO_WORKER_SOCKET_DIR", "data/worker"))
    ap.add_argument("--host", default="", help="兼容旧参数：同时设置 http/ws host")
    ap.add_argument("--http-host", default=os.getenv("NAO_API_HOST", "127.0.0.1"))
    ap.add_argument("--ws-host", default=os.getenv("NAO_LISTEN_HOST", "0.0.0.0"))
    ap.add_argument("--http-port", type=int, default=int(os.getenv("NAO_API_PORT", "27004")))
    ap.add_argument("--allow-public", action="store_true",
                    help="允许 HTTP 监听非 loopback（默认拒绝）")
    ap.add_argument("--ws-port", type=int, default=int(os.getenv("NAO_WS_PORT", "3001")))
    args = ap.parse_args()
    if args.host:
        args.http_host = args.ws_host = args.host
    try:
        is_loop = ip_address(args.http_host).is_loopback
    except ValueError:
        is_loop = args.http_host in ("localhost",)
    if not is_loop and not args.allow_public:
        raise SystemExit("HTTP 监听不是 loopback；如确需公网请显式加 --allow-public")
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
