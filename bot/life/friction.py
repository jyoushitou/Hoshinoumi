# ===================== 摩擦（v13-U20） =====================
# 期待 → 失落 → 冷战 → 和好。所有负面状态都有上限和恢复路径。
#
# 红线（写死在代码里，不许绕过）：
#   冷战最长 24 小时，到点自动结束
#   怨念一周最多 1 次
#   失落最多累计 3 次，到顶就进入冷战而不是无限累积

import json
import random
import re
import time as _time
from datetime import datetime

from ..config import CST
from ..log import log_system

EXPECT_TTL = 8 * 3600        # 她叮嘱之后 8 小时内没回应 → 失望
COLD_WAR_MAX = 24 * 3600     # 冷战最长 24 小时
DISAPPOINT_MAX = 3           # 累积 3 次失望 → 冷战
GRUDGE_WEEK = 7 * 86400      # 怨念：一周最多一次
GRUDGE_LIMIT = 1

CARE_PATTERN = re.compile(r"(晚安|早点睡|记得吃饭|别忘了|注意身体|早点回来|别熬夜)")

PHASES = ("calm", "waiting", "letdown", "cold")


def _now(now=None):
    return (now or datetime.now(CST)).timestamp()


def empty_state():
    return {
        "expect_ts": 0.0,       # 说这句话的时间
        "expect_text": "",      # 说了什么（「早点睡」）
        "disappoint": 0,        # 累计失望次数
        "cold_ts": 0.0,         # 冷战开始时间
        "last_grudge": 0.0,     # 上次怨念时间
        "ignored_replies": 0,   # 冷战中收到几条消息（用于和好）
    }


# ===================== 存取 =====================

def load(tid):
    from ..core import state as cfg
    tid = str(tid)
    if tid in cfg.friction_states:
        return cfg.friction_states[tid]
    st = empty_state()
    try:
        from ..infra.repo_memory import load_friction
        raw = load_friction(tid)
        if raw:
            st.update(json.loads(raw))
    except Exception:
        pass
    cfg.friction_states[tid] = st
    return st


def save(tid):
    from ..core import state as cfg
    tid = str(tid)
    st = cfg.friction_states.get(tid)
    if not st:
        return False
    try:
        from ..infra.repo_memory import save_friction
        save_friction(tid, json.dumps(st, ensure_ascii=False, separators=(",", ":")))
        return True
    except Exception:
        return False


# ===================== 事件 =====================

def note_expectation(tid, text, now=None):
    """她说了一句关心的话 → 记下期待"""
    st = load(tid)
    if not CARE_PATTERN.search(text or ""):
        return False
    st["expect_ts"] = _now(now)
    st["expect_text"] = CARE_PATTERN.search(text).group(1)
    save(tid)
    return True


def on_user_message(tid, now=None):
    """收到他的消息：清期待，可能和好"""
    st = load(tid)
    now_ts = _now(now)
    changed = False

    if st["expect_ts"]:
        st["expect_ts"] = 0.0
        st["expect_text"] = ""
        changed = True

    if st["cold_ts"]:
        st["ignored_replies"] += 1
        # 和好：冷战期间他说了 3 句，或超过 12 小时，或直接说对不起
        if st["ignored_replies"] >= 3 or (now_ts - st["cold_ts"]) > 12 * 3600:
            st["cold_ts"] = 0.0
            st["ignored_replies"] = 0
            st["disappoint"] = 0
            log_system(f"和好: {tid} 冷战结束")
        changed = True

    if changed:
        save(tid)
    return changed


def apologize(tid, now=None):
    """他说了软话：立刻和好，并进入慢修复"""
    st = load(tid)
    if not st["cold_ts"]:
        return False
    st["cold_ts"] = 0.0
    st["ignored_replies"] = 0
    st["disappoint"] = 0
    save(tid)
    try:
        from . import relation
        relation.repair(tid, reason="道歉")
    except Exception:
        pass
    log_system(f"和好: {tid} 被哄好了")
    return True


def refresh(tid, last_user_ts=None, now=None):
    """主循环/回复前调用：推进状态（失望、冷战开始、冷战到期）"""
    st = load(tid)
    now_ts = _now(now)
    changed = False

    # 1) 期待过期 → 失望 +1
    if st["expect_ts"] and now_ts - st["expect_ts"] > EXPECT_TTL:
        st["expect_ts"] = 0.0
        st["disappoint"] = min(DISAPPOINT_MAX, st["disappoint"] + 1)
        log_system(f"失落: {tid} 他 {st['expect_text']} 没回，失望 {st['disappoint']}")
        try:
            from . import relation
            relation.apply_delta(tid, -0.03, "期待超时", "minor")
        except Exception:
            pass
        changed = True

    # 2) 失望到顶 → 冷战
    if st["disappoint"] >= DISAPPOINT_MAX and not st["cold_ts"]:
        st["cold_ts"] = now_ts
        st["ignored_replies"] = 0
        log_system(f"冷战: {tid} 开始（最多 24 小时）")
        try:
            from . import relation
            relation.apply_delta(tid, -0.08, "进入冷战", "major")
        except Exception:
            pass
        changed = True

    # 3) 冷战到期 → 自动和好
    if st["cold_ts"] and now_ts - st["cold_ts"] > COLD_WAR_MAX:
        st["cold_ts"] = 0.0
        st["ignored_replies"] = 0
        st["disappoint"] = 0
        log_system(f"和好: {tid} 冷战到点自动结束")
        changed = True

    if changed:
        save(tid)
    return st


def grudge_allowed(tid, now=None):
    """怨念一周最多一次"""
    st = load(tid)
    now_ts = _now(now)
    if now_ts - st.get("last_grudge", 0.0) < GRUDGE_WEEK:
        return False
    st["last_grudge"] = now_ts
    save(tid)
    try:
        from . import relation
        relation.apply_delta(tid, -0.15, "长期怨念", "major")
    except Exception:
        pass
    return True


# ===================== 渲染 =====================

def phase(tid, now=None):
    st = load(tid)
    now_ts = _now(now)
    if st["cold_ts"]:
        return "cold"
    if st["expect_ts"]:
        return "waiting"
    if st["disappoint"] > 0:
        return "letdown"
    return "calm"


def prompt_line(tid, now=None):
    """给 prompt 用的一句话；平静期返回空"""
    p = phase(tid, now)
    if p == "cold":
        return ("（你在生闷气：他之前晾着你。回话要短、要冷，"
                "别主动解释，但也别骂人——说两句就该消气了）")
    if p == "letdown":
        return "（你有点失落：之前叮嘱他的事，他没回。语气淡一点，别撒娇）"
    if p == "waiting":
        return ""
    return ""

# ===================== 欲言又止（v13-G47） =====================
# 偶尔把最后一句咽回去，换成「算了。」

TRAIL_OFF_PROB = 0.03


def maybe_trail_off(text, rng=None):
    """小概率把最后一句换成「算了。」"""
    rng = rng or random
    if not text or rng.random() > TRAIL_OFF_PROB:
        return text
    lines = [ln for ln in str(text).split("\n") if ln.strip()]
    if len(lines) < 2:
        return text
    return "\n".join(lines[:-1] + ["算了。"])


def is_sorry(text):
    """他说了软话没有"""
    return any(w in (text or "") for w in ("对不起", "抱歉", "我错了", "别生气了", "是我不好"))