# ===================== server 包 =====================
# HTTP API（v5-R5）：配置 / 工具 / 路由 / 启动，四块分开
# v19.4：不在包 __init__ import http_api，避免 http_api → server 包的反向环
