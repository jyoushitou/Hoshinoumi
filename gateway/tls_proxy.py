#!/usr/bin/env python3
"""v22.1 网关 TLS 终止代理（stdlib asyncio）。

    python3 gateway/tls_proxy.py \
        --cert /etc/nao/fullchain.pem \
        --key  /etc/nao/privkey.pem \
        --listen 0.0.0.0:27443 \
        --backend 127.0.0.1:27005

只做字节流转发；HTTP/JWT/限流仍由 rec_gateway 处理。
没有证书时不要启动；本地开发可以继续直连 HTTP 27005。
"""

import argparse
import asyncio
import ssl
import sys


def parse_addr(value, default_host, default_port):
    if ":" in value:
        host, port = value.rsplit(":", 1)
        return host or default_host, int(port)
    return default_host, int(value)


async def pump(reader, writer):
    try:
        while True:
            data = await reader.read(65536)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except (ConnectionError, asyncio.CancelledError):
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass


async def handle(client_reader, client_writer, backend_host, backend_port):
    try:
        backend_reader, backend_writer = await asyncio.open_connection(
            backend_host, backend_port)
    except Exception as e:
        print(f"[tls] 后端连接失败 {backend_host}:{backend_port}: {e}", file=sys.stderr)
        client_writer.close()
        return
    await asyncio.gather(
        pump(client_reader, backend_writer),
        pump(backend_reader, client_writer),
    )


async def serve(args):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(args.cert, args.key)
    host, port = args.listen
    backend_host, backend_port = args.backend
    server = await asyncio.start_server(
        lambda r, w: handle(r, w, backend_host, backend_port),
        host, port, ssl=ctx)
    print(f"[tls] HTTPS 监听 {host}:{port} -> {backend_host}:{backend_port}")
    async with server:
        await server.serve_forever()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cert", required=True)
    ap.add_argument("--key", required=True)
    ap.add_argument("--listen", default="0.0.0.0:27443")
    ap.add_argument("--backend", default="127.0.0.1:27005")
    args = ap.parse_args()
    args.listen = parse_addr(args.listen, "0.0.0.0", 27443)
    args.backend = parse_addr(args.backend, "127.0.0.1", 27005)
    try:
        asyncio.run(serve(args))
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"[tls] 启动失败: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
