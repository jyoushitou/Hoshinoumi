# ===================== HTTP 会话 =====================
# 统一的 requests 会话工厂：带连接池、不自动重试
# 迁移自 config.py（v5-R2），行为与迁移前完全一致

import requests  # HTTP 客户端
from requests.adapters import HTTPAdapter  # 连接池适配器


def create_http_session():
    """创建带连接池的HTTP会话，不重试"""
    s = requests.Session()  # 创建会话
    s.mount("https://", HTTPAdapter(max_retries=0))  # HTTPS 挂载适配器，不重试
    s.mount("http://", HTTPAdapter(max_retries=0))  # HTTP 挂载适配器，不重试
    return s
