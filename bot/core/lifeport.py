# ===================== 生活能力端口（v17.15 债二） =====================
# 目的：让 `ai` 层**不 import `life`**。
#
# 以前：ai/client.py 顶部 from ..life.state import ...（8 个 life 模块）
#       → AI 层直接依赖她的生活，任何 life 改动都会波及模型调用
# 现在：life 启动时把自己的能力注册进来；ai 只认名字。
#
#   # life 包（或 bootstrap）里
#   from ..core.lifeport import register
#   register("state_line", lambda tid: describe(current(tid=tid)))
#
#   # ai 里
#   from ..core.lifeport import life
#   life.state_line(tid)      # 没注册就返回默认值，不抛
#
# 纪律：端口只做「取值」，不做业务判断；缺实现不算错。

_DEFAULTS = {
    "state_line": "",
    "friction_refresh": None,
    "friction_line": "",
    "ensure_daily": None,
    "relation_line": "",
    "touch_talk": None,
    "relation_bump": None,
    "habit_line": "",
    "milestone_line": "",
    "digest_line": "",
    "reading_line": "",
    "condense": None,
}

_impl = {}


def register(name, fn):
    """注册一个能力；同名后注册的覆盖先注册的"""
    if name not in _DEFAULTS:
        raise KeyError(f"未定义的生活能力：{name}")
    _impl[name] = fn
    return fn


def unregister(name):
    _impl.pop(name, None)


def available(name=None):
    if name:
        return name in _impl
    return sorted(_impl)


class _LifePort:
    """ai 层用的只读门面：调用已注册实现，缺失时返回默认值"""

    def __getattr__(self, name):
        if name not in _DEFAULTS:
            raise AttributeError(name)
        default = _DEFAULTS[name]
        fn = _impl.get(name)
        if fn is None:
            def _fallback(*a, **kw):
                return default
            return _fallback
        return fn


life = _LifePort()
