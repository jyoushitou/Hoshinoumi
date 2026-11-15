#!/usr/bin/env python3
# ===================== v25.5 热更新演练检查 =====================
# 只做只读检查：current、worker socket、ingress 端口、/api/health。

import argparse
import asyncio
import os
import socket
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


async def health(api_sock):
    import aiohttp
    try:
        conn = aiohttp.UnixConnector(path=api_sock)
        async with aiohttp.ClientSession(connector=conn) as s:
            async with s.get("http://worker/api/health", timeout=2) as r:
                return r.status
    except Exception as e:
        return f"ERR {e}"


def port_open(host, port):
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=str(ROOT / "data" / "workers"))
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--http-port", type=int, default=27004)
    ap.add_argument("--ws-port", type=int, default=3001)
    args = ap.parse_args()
    base = Path(args.base)
    cur = base / "current"
    print(f"current: {os.readlink(cur) if cur.is_symlink() else (cur.read_text().strip() if cur.exists() else 'MISSING')}")
    api = base / "current" / "api.sock"
    qq = base / "current" / "qq.sock"
    print(f"api.sock: {api.exists()}  qq.sock: {qq.exists()}")
    print(f"health: {await health(str(api))}")
    print(f"ingress http {args.http_port}: {port_open(args.host, args.http_port)}")
    print(f"ingress ws {args.ws_port}: {port_open(args.host, args.ws_port)}")


if __name__ == "__main__":
    asyncio.run(main())
