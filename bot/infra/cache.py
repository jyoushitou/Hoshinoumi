# ===================== 进程内 TTL 缓存（v18.13） =====================
# 只给热点只读用；写后必须 invalidate。不引入 Redis。
#
#   cache.get(key) / set(key, value, ttl) / invalidate(prefix) / stats()

import time

_store = {}          # key -> (expire_at, value)
_hits = 0
_misses = 0


def _now():
    return time.time()


def get(key):
    global _hits, _misses
    item = _store.get(key)
    if item is None:
        _misses += 1
        return None
    expire_at, value = item
    if expire_at <= _now():
        _store.pop(key, None)
        _misses += 1
        return None
    _hits += 1
    return value


def set(key, value, ttl=5.0):
    _store[key] = (_now() + max(0.0, float(ttl)), value)
    return value


class Namespace:
    """命名空间视图：统一前缀，避免不同模块手写 key 前缀"""

    def __init__(self, name):
        self.prefix = f"{name}:"

    def get(self, key):
        return get(self.prefix + str(key))

    def set(self, key, value, ttl=5.0):
        return set(self.prefix + str(key), value, ttl)

    def invalidate(self, key=None):
        if key is None:
            invalidate(self.prefix)
        else:
            invalidate(self.prefix + str(key))


def namespace(name):
    return Namespace(name)


def invalidate(prefix=None):
    """删 key（前缀）或全部"""
    if prefix is None:
        _store.clear()
        return
    for k in list(_store):
        if str(k).startswith(prefix):
            _store.pop(k, None)


def stats():
    total = _hits + _misses
    return {"size": len(_store), "hits": _hits, "misses": _misses,
            "hit_rate": (_hits / total) if total else 0.0}


def reset_stats():
    global _hits, _misses
    _hits = 0
    _misses = 0


def describe():
    s = stats()
    return (f"🧠 查询缓存（TTL）：{s['size']} 条 | 命中 {s['hits']} | "
            f"未命中 {s['misses']} | 命中率 {s['hit_rate']:.0%}")
