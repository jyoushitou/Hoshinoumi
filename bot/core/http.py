# ===================== HTTP 会话 =====================
# 统一的 requests 会话工厂：带连接池、不自动重试
# v8-E27：模型调用在 asyncio.to_thread 里跑，每个线程复用自己的 Session，
#         不再每次请求都新建（省掉 TLS 握手和连接建立）。

import threading

import requests  # HTTP 客户端
from requests.adapters import HTTPAdapter  # 连接池适配器

_local = threading.local()  # 每线程一个 Session


def create_http_session():
    """创建带连接池的HTTP会话，不重试（一次性用）"""
    s = requests.Session()  # 创建会话
    s.mount("https://", HTTPAdapter(max_retries=0))  # HTTPS 挂载适配器，不重试
    s.mount("http://", HTTPAdapter(max_retries=0))  # HTTP 挂载适配器，不重试
    return s


def get_http_session():
    """取当前线程的常驻会话（第一次调用时创建）"""
    session = getattr(_local, "session", None)
    if session is None:
        session = create_http_session()
        _local.session = session
    return session


def close_thread_session():
    """关闭当前线程的会话（退出时可选调用）"""
    session = getattr(_local, "session", None)
    if session is not None:
        try:
            session.close()
        except Exception:
            pass
        _local.session = None
