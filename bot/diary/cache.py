# ===================== 日记缓存（v21.8 统一 TTL 缓存） =====================
# 迁移自 diary.py；不再自建 dict，统一走 infra.cache 的 diary: 命名空间。

from ..infra import cache

CACHE_TTL = 600  # 缓存有效期（秒）= 10 分钟
MAX_CACHE = 20   # 兼容旧常量；统一缓存用 TTL 淘汰
_ns = cache.namespace("diary")


def get(key):
    """取缓存，未命中或过期返回 None"""
    return _ns.get(key)


def peek(key):
    """只查有没过期判断，返回 text 或 None（概览用）"""
    return _ns.get(key)


def put(key, text):
    """写入缓存，统一 10 分钟 TTL"""
    return _ns.set(key, text, ttl=CACHE_TTL)


def clear():
    _ns.invalidate()
