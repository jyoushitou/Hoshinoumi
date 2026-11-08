# ===================== HTTP 服务器装配 =====================
# 鉴权中间件 + 路由注册 + 启动
# 迁移自 api_server.py（v5-R5）

import asyncio
import hmac

from aiohttp import web

from ..log import log_system
from . import config as apicfg
from .common import json_response
from .routes_meta import (
    handle_health, handle_status, handle_usage,
    handle_memory, handle_logs, handle_get_token,
)
from .routes_chat import handle_chat, handle_command


@web.middleware
async def auth_middleware(request, handler):
    """Bearer Token 鉴权；/api/health 免鉴权"""
    if request.path == "/api/health":
        return await handler(request)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return json_response(
            {"error": "missing_auth_header", "message": "缺少 Authorization header"},
            status=401
        )
    token = auth_header[7:]
    if not hmac.compare_digest(token, apicfg.API_TOKEN):
        return json_response(
            {"error": "invalid_token", "message": "Token 无效"},
            status=403
        )
    return await handler(request)


async def start_api_server():
    """启动 HTTP API 服务器，返回 AppRunner"""
    _semaphore = asyncio.Semaphore(apicfg.MAX_CONCURRENT_REQUESTS)
    apicfg.load_api_token()

    app = web.Application(middlewares=[auth_middleware])
    app.router.add_get("/api/health", handle_health)
    app.router.add_get("/api/status", handle_status)
    app.router.add_get("/api/usage", handle_usage)
    app.router.add_get("/api/memory", handle_memory)
    app.router.add_get("/api/logs", handle_logs)
    app.router.add_get("/api/token", handle_get_token)
    app.router.add_post("/api/chat", handle_chat)
    app.router.add_post("/api/command", handle_command)

    runner = web.AppRunner(app, handle_signals=False)
    await runner.setup()
    site = web.TCPSite(runner, apicfg.API_HOST, apicfg.API_PORT, reuse_address=True, reuse_port=True)
    await site.start()

    log_system(f"API 服务器已启动: http://{apicfg.API_HOST}:{apicfg.API_PORT}")
    log_system(f"API Token: {apicfg.API_TOKEN[:12]}...")
    log_system(f"最大并发: {apicfg.MAX_CONCURRENT_REQUESTS}")

    return runner
