# ===================== server 包 =====================
# HTTP API（v5-R5）：配置 / 工具 / 路由 / 启动，四块分开
# v19.4：不在包 __init__ import http_api，避免 http_api → server 包的反向环。


def __getattr__(name):
    """兼容旧的 from bot.server import ...，但不在导入时形成环"""
    if name == "start_api_server":
        from .http_api import start_api_server

        return start_api_server
    if name in ("format_api_token_info", "load_api_token"):
        from . import config

        return getattr(config, name)
    raise AttributeError(name)
