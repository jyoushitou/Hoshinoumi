# ===================== server 包 =====================
# HTTP API（v5-R5）：配置 / 工具 / 路由 / 启动，四块分开
# v19.4：不在包 __init__ import http_api，避免 http_api → server 包的反向环。


def __getattr__(name):
    """兼容 from botv.server import start_api_server，但不在导入时形成环"""
    if name == "start_api_server":
        from .http_api import start_api_server

        return start_api_server
    raise AttributeError(name)
