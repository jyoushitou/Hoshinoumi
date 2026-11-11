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


def setup_life_bridge():
    """把 life 包的能力一次性注册进来（bootstrap 调一次，幂等）"""
    from ..life import digest as life_digest
    from ..life import friction as life_friction
    from ..life import reading as life_reading
    from ..life import relation as life_relation
    from ..life import state as life_state
    from ..life.events import ensure_daily_life
    from ..life.habit import describe as habit_describe, phrases_for
    from ..life.milestone import milestone_text
    from ..life.state import describe as state_describe
    from ..life.state import touch_talk

    register("state_line", lambda tid: state_describe(life_state.current(tid=tid)))
    register("friction_refresh", lambda tid: life_friction.refresh(tid))
    register("friction_line", lambda tid: life_friction.prompt_line(tid))
    register("ensure_daily", lambda: ensure_daily_life())
    register("relation_line", lambda tid: life_relation.describe(tid)
             + (("｜" + life_relation.addressing(tid)) if life_relation.addressing(tid) else ""))
    register("touch_talk", lambda tid: touch_talk(tid=tid))
    register("relation_bump", lambda tid: life_relation.bump(tid))
    register("habit_line", lambda tid: habit_describe(phrases_for(tid)))
    register("milestone_line", lambda tid: milestone_text(tid))
    register("digest_line", lambda tid: life_digest.describe(tid))
    register("reading_line", lambda tid: life_reading.describe(tid))
    register("condense", lambda tid, summarize=None: life_digest.maybe_condense(tid, summarize))
    return available()


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
