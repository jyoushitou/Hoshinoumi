# ===================== life 能力装配（v19.4） =====================
# 从 core.lifeport 移出：core 只保留注册表/门面，不再 import life。

from ..core.lifeport import available, register


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
