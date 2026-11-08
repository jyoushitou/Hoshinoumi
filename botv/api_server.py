# ===================== 兼容层 =====================
# v5-R5：HTTP API 已迁至 botv/server/*
# 本文件只做转发，保证旧 import 路径仍然可用

from .server import start_api_server, format_api_token_info  # noqa: F401
from .server.config import (  # noqa: F401
    API_HOST, API_PORT, API_TOKEN, API_TOKEN_KEY_NAME, MAX_CONCURRENT_REQUESTS,
)
