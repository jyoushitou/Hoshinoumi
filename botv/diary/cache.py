# ===================== 日记缓存 =====================
# 内存缓存 10 分钟，最多 20 条
# 迁移自 diary.py（v5-R5）

from datetime import datetime

CACHE_TTL = 600  # 缓存有效期（秒）= 10 分钟
MAX_CACHE = 20   # 缓存最大条数

_cache = {}  # {key: (生成时间戳, 日记内容)}


def get(key):
    """取缓存，未命中或过期返回 None"""
    entry = _cache.get(key)
    if not entry:
        return None
    gen_time, text = entry
    if datetime.now().timestamp() - gen_time < CACHE_TTL:
        return text
    return None


def peek(key):
    """只查有没过期判断，返回 (text) 或 None（概览用）"""
    entry = _cache.get(key)
    return entry[1] if entry else None


def put(key, text):
    """写入缓存，超限时删除最旧的一条"""
    _cache[key] = (datetime.now().timestamp(), text)
    if len(_cache) > MAX_CACHE:
        oldest_key = min(_cache, key=lambda k: _cache[k][0])
        del _cache[oldest_key]
