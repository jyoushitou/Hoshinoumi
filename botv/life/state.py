# ===================== 状态向量（v9-U4） =====================
# 她有自己的状态：心情 / 精力 / 孤独，而不是每句话都从零开始。
# 核心原则：**数值永远不进 prompt**，只用来渲染成一句人话。

import json
import random
import time as _time
from datetime import datetime

from ..config import CST

BASE = {"mood": 0.10, "energy": 0.70, "lonely": 0.15}  # 基线（每天回到这里）
CLAMP = {"mood": (-1.0, 1.0), "energy": (0.0, 1.0), "lonely": (0.0, 1.0)}
K = 0.15          # 每小时向基线回归的比例
ALONE_PER_HOUR = 0.05   # 没人说话，孤独每小时 +5%
TALK_RELIEF = 0.06      # 每收到一条消息，孤独 -6%

_rng = random.Random()


def default_state():
    s = dict(BASE)
    s["diary_bias"] = 0.0  # 昨天日记带来的情绪余韵（v9-U11）
    return s


def clamp(state):
    """把每个维度压回合法区间"""
    out = {}
    for key, (lo, hi) in CLAMP.items():
        out[key] = max(lo, min(hi, float(state.get(key, BASE[key]))))
    if "diary_bias" in state:  # 只在有时才保留，避免污染只含三键的旧数据
        out["diary_bias"] = max(-0.15, min(0.15, float(state.get("diary_bias") or 0.0)))
    return out


def tick(state, hours, now=None):
    """按经过的小时数推进状态

    - 向基线回归（k(base - s)）
    - 独处累积孤独
    - 深夜掉精力
    """
    hours = max(0.0, min(float(hours or 0), 72.0))  # 最多补 3 天，防止停机太久一次跳飞
    s = clamp(state)
    factor = 1 - (1 - K) ** hours  # 指数回归：时间越长越贴近基线，但永不越过

    # 孤独不是直接扣心情，而是**把心情的基线往下拉**：
    # 这样无论一次补 72 小时还是逐小时推进，稳定点都一样。
    lonely_after = min(1.0, s["lonely"] + ALONE_PER_HOUR * hours)
    lonely_avg = (s["lonely"] + lonely_after) / 2
    mood_target = BASE["mood"] - 0.6 * lonely_avg + s.get("diary_bias", 0.0)

    s["mood"] += factor * (mood_target - s["mood"])
    if s.get("diary_bias"):
        s["diary_bias"] = round(s["diary_bias"] * (1 - factor), 4)  # 余韵随时间淡去
    s["energy"] += factor * (BASE["energy"] - s["energy"])
    s["lonely"] = lonely_after

    if now is not None:
        hour = now.hour
        if 0 <= hour < 6:
            s["energy"] -= 0.08 * hours   # 熬夜掉精力
        elif 7 <= hour < 10:
            s["energy"] += 0.04 * hours   # 早上回一点
    return clamp(s)


def on_talk(state, warmth=1.0):
    """有人找她说话：孤独下降，心情微升"""
    s = clamp(state)
    s["lonely"] -= TALK_RELIEF * warmth
    s["mood"] += 0.015 * warmth
    return clamp(s)


def on_ignored(state, hours=1.0):
    """被已读不回：孤独和烦躁一起涨"""
    s = clamp(state)
    s["lonely"] += 0.06 * hours
    s["mood"] -= 0.04 * hours
    return clamp(s)


def _mood_word(v):
    if v >= 0.55:
        return "心情挺好"
    if v >= 0.2:
        return "心情还行"
    if v > -0.2:
        return "情绪平平"
    if v > -0.55:
        return "有点烦"
    return "很烦"


def _energy_word(v):
    if v >= 0.75:
        return "精力充足"
    if v >= 0.45:
        return "还算清醒"
    if v >= 0.2:
        return "有点累"
    return "困得不行"


def _lonely_word(v):
    if v >= 0.65:
        return "很久没人说话了，有点闷"
    if v >= 0.35:
        return "有点想找人聊两句"
    return ""


def describe(state, now=None):
    """把数值渲染成一句人话（数值本身绝不出现）"""
    s = clamp(state)
    parts = [_mood_word(s["mood"]), _energy_word(s["energy"])]
    lonely = _lonely_word(s["lonely"])
    if lonely:
        parts.append(lonely)
    return "，".join(parts) + "。"


# ===================== 存取 =====================

def to_json(state):
    return json.dumps(clamp(state), ensure_ascii=False, separators=(",", ":"))


def from_json(text, fallback=None):
    """解析状态；缺的字段用默认值补齐（兼容旧的三键数据）"""
    base = dict(fallback or default_state())
    try:
        data = json.loads(text or "{}")
        if isinstance(data, dict):
            for k in list(base.keys()):
                if k in data:
                    base[k] = data[k]
    except Exception:
        pass
    return clamp(base)


def load():
    """从数据库读状态；读不到就用默认值"""
    try:
        from ..infra.repo_memory import load_state_json
        raw = load_state_json()
        return from_json(raw) if raw else default_state()
    except Exception:
        return default_state()


def save(state):
    """写回数据库（失败不影响回复）"""
    try:
        from ..infra.repo_memory import save_state_json
        save_state_json(to_json(state))
        return True
    except Exception:
        return False


# ===================== 运行时入口 =====================

TICK_MIN_HOURS = 0.2  # 至少过 12 分钟才推进，避免频繁写库


def current(now=None):
    """取当前状态：按流逝的时间推进，必要时落库"""
    from ..core import state as cfg
    now = now or datetime.now(CST)
    if not getattr(cfg, "bot_state", None):
        cfg.bot_state = load()
        cfg.bot_state_ts = _time.time()
    elapsed = max(0.0, (_time.time() - getattr(cfg, "bot_state_ts", 0.0)) / 3600.0)
    if elapsed >= TICK_MIN_HOURS:
        cfg.bot_state = tick(cfg.bot_state, elapsed, now)
        cfg.bot_state_ts = _time.time()
        save(cfg.bot_state)
    return cfg.bot_state


def touch_talk(warmth=1.0):
    """聊了一句：缓解孤独，并落库"""
    from ..core import state as cfg
    s = current()
    cfg.bot_state = on_talk(s, warmth)
    save(cfg.bot_state)
    return cfg.bot_state


def touch_ignored(hours=1.0):
    """被晾着：孤独与烦躁上升"""
    from ..core import state as cfg
    s = current()
    cfg.bot_state = on_ignored(s, hours)
    save(cfg.bot_state)
    return cfg.bot_state
