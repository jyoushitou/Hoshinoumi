# ===================== repo 池会话包装（v28.1） =====================
# 目标：repo_* 的每个 DB 函数在一个 pooled_cursor 里执行；
# 函数内部原有的 get_cursor() 会返回同一个池游标。
# 旧 conn.get_cursor() 仍可用，未包装的调用保持线程本地兼容。

import functools
import inspect

from .pool import pooled_cursor

_ENABLED = False


def enable():
    global _ENABLED
    _ENABLED = True


def disable():
    global _ENABLED
    _ENABLED = False


def enabled():
    return _ENABLED


def pooled(fn):
    if getattr(fn, "_nao_pooled", False):
        return fn

    try:
        sig = inspect.signature(fn)
    except Exception:
        sig = None

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if not _ENABLED:
            return fn(*args, **kwargs)
        # 调用方显式传 cursor：沿用它的连接/事务，不另开池连接。
        if sig is not None and "cursor" in sig.parameters:
            try:
                bound = sig.bind_partial(*args, **kwargs)
                if bound.arguments.get("cursor") is not None:
                    return fn(*args, **kwargs)
            except TypeError:
                pass
        with pooled_cursor():
            return fn(*args, **kwargs)

    wrapper._nao_pooled = True
    return wrapper


def install_module(namespace):
    """在 repo 模块末尾调用：包装本模块中直接调用 get_cursor 的函数。"""
    for name, obj in list(namespace.items()):
        if not inspect.isfunction(obj) or name.startswith("__"):
            continue
        if getattr(obj, "_nao_pooled", False):
            continue
        if obj.__module__ != namespace.get("__name__"):
            continue
        try:
            src = inspect.getsource(obj)
        except Exception:
            continue
        if "get_cursor" not in src:
            continue
        namespace[name] = pooled(obj)

# v28.1：repo 函数进入统一池会话
from .repo_pool import install_module as _install_repo_pool
_install_repo_pool(globals())
