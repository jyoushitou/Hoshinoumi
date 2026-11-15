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
from ipaddress import ip_address

import websockets

from .core import worker

def frame_limit():
    from .server.frame import MAX_BODY
    return MAX_BODY + 64


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


async def _tcp_copy(src, dst):
    try:
        while True:
            data = await src.read(65536)
            if not data:
                break
            dst.write(data)
            await dst.drain()
    except Exception:
        pass
    finally:
        try:
            dst.close()
        except Exception:
            pass


async def _tcp_proxy(reader, writer):
    """27004 L4：把 8+4+body 帧原样转给 current worker 的 internal.sock。"""
    path = worker.active_socket("internal.sock")
    try:
        ur, uw = await asyncio.open_unix_connection(path)
    except Exception:
        try:
            writer.close()
        except Exception:
            pass
        return
    await asyncio.gather(_tcp_copy(reader, uw), _tcp_copy(ur, writer))
    try:
        writer.close()
    except Exception:
        pass


async def main_async(args):
    worker.set_directory(args.worker_dir)
    tcp_proxy = None
    runner = None
    if args.protocol == "tcp":
        tcp_proxy = await asyncio.start_server(
            _tcp_proxy, args.http_host, args.http_port,
            limit=frame_limit())
        print(f"[ingress] TCP {args.http_host}:{args.http_port} "
              f"WS {args.ws_host}:{args.ws_port} -> {args.worker_dir}")
    else:
        from aiohttp import web
        app = web.Application()
        app.router.add_route("*", "/{tail:.*}", lambda r: _http_proxy(r))
        runner = web.AppRunner(app, handle_signals=False)
        await runner.setup()
        site = web.TCPSite(runner, args.http_host, args.http_port)
        await site.start()
        print(f"[ingress] HTTP {args.http_host}:{args.http_port} "
              f"WS {args.ws_host}:{args.ws_port} -> {args.worker_dir}")

    ws = await websockets.serve(_ws_proxy, args.ws_host, args.ws_port,
                                ping_interval=20, ping_timeout=60)
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
            if runner is not None:
                try:
                    await asyncio.wait_for(runner.cleanup(), 3)
                except Exception:
                    pass
            if tcp_proxy is not None:
                tcp_proxy.close()
                try:
                    await asyncio.wait_for(tcp_proxy.wait_closed(), 3)
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
    ap.add_argument("--protocol", choices=("http", "tcp"),
                    default=os.getenv("NAO_INGRESS_PROTOCOL", "tcp"))
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
