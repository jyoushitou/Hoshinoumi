# ===================== 兼容层 =====================
# v5-R5：HTTP API 已迁至 bot/server/*
# 本文件只做转发，保证旧 import 路径仍然可用

def start_api_server(*args, **kwargs):
    """延迟导入 aiohttp，避免测试/CLI 仅 import 时缺依赖。"""
    from .server.http_api import start_api_server as _start

    return _start(*args, **kwargs)


from .server.config import format_api_token_info  # noqa: F401,E402
from .server.config import (  # noqa: F401
    API_HOST, API_PORT, API_TOKEN, API_TOKEN_KEY_NAME, MAX_CONCURRENT_REQUESTS,
)
