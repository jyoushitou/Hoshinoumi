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
# v14-A2：基线可由角色卡覆盖（读不到就用上面的内置值）
try:
    from ..ai.persona_loader import load_state_base as _load_base
    _card_base = _load_base()
    if _card_base:
        BASE = {k: float(_card_base.get(k, BASE[k])) for k in BASE}
except Exception:
    pass

K = 0.15          # 每小时向基线回归的比例
ALONE_PER_HOUR = 0.05   # 没人说话，孤独每小时 +5%
TALK_RELIEF = 0.06      # 每收到一条消息，孤独 -6%

_rng = random.Random()


def default_state():
    s = dict(BASE)
    s["diary_bias"] = 0.0  # 昨天日记带来的情绪余韵（v9-U11）
    # v18.11：情绪标签跨天保留（半衰期 3/5 天）
    s["emotion"] = ""
    s["emotion_at"] = 0.0
    s["emotion_power"] = 0.0
    return s


def clamp(state):
    """把每个维度压回合法区间"""
    out = {}
    for key, (lo, hi) in CLAMP.items():
        out[key] = max(lo, min(hi, float(state.get(key, BASE[key]))))
    if "diary_bias" in state:  # 只在有时才保留，避免污染只含三键的旧数据
        out["diary_bias"] = max(-0.15, min(0.15, float(state.get("diary_bias") or 0.0)))
    if "emotion" in state:
        out["emotion"] = str(state.get("emotion") or "")
        out["emotion_at"] = float(state.get("emotion_at") or 0.0)
        out["emotion_power"] = max(0.0, min(1.0, float(state.get("emotion_power") or 0.0)))
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

    # v18.11：情绪标签按半衰期衰减（强烈 5 天 / 普通 3 天）
    if s.get("emotion") and s.get("emotion_power"):
        days = hours / 24.0
        half = 5.0 if float(s["emotion_power"]) >= 0.8 else 3.0
        s["emotion_power"] = float(s["emotion_power"]) * (0.5 ** (days / half))

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


def load(tid=None):
    """读某个对象的状态；不传就是机器人自己（v14.1-D1：按人分开）"""
    try:
        from ..infra.repo_memory import load_state_json, STATE_TARGET
        raw = load_state_json(str(tid) if tid else STATE_TARGET)
        return from_json(raw) if raw else default_state()
    except Exception:
        return default_state()


def save(state, tid=None):
    """写回某个对象的状态（失败不影响回复）"""
    try:
        from ..infra.repo_memory import save_state_json, STATE_TARGET
        save_state_json(to_json(state), str(tid) if tid else STATE_TARGET)
        return True
    except Exception:
        return False


# ===================== 运行时入口 =====================

TICK_MIN_HOURS = 0.2  # 至少过 12 分钟才推进，避免频繁写库


def current(now=None, tid=None):
    """取某个对象的当前状态（v14.1-D1：按人分开，不传就是机器人自己）"""
    from ..core import state as cfg
    now = now or datetime.now(CST)
    key = str(tid) if tid else "__self__"
    entries = getattr(cfg, "bot_states", None)
    if entries is None:
        entries = {}
        cfg.bot_states = entries

    entry = entries.get(key)
    if not entry:
        entry = {"s": load(tid), "ts": _time.time()}
        entries[key] = entry

    elapsed = max(0.0, (_time.time() - entry["ts"]) / 3600.0)
    if elapsed >= TICK_MIN_HOURS:
        entry["s"] = tick(entry["s"], elapsed, now)
        entry["ts"] = _time.time()
        save(entry["s"], tid)
    return entry["s"]


def touch_talk(warmth=1.0, tid=None):
    """聊了一句：缓解孤独，并落库（同时更新机器人自己的状态）"""
    s = current(tid=tid)
    new_s = on_talk(s, warmth)
    save(new_s, tid)
    if tid:  # 主动消息用的是「她自己」的状态，也要跟着变
        g = current(tid=None)
        save(on_talk(g, warmth), None)
    return new_s


def touch_ignored(hours=1.0, tid=None):
    """被晾着：孤独与烦躁上升（同时更新机器人自己的状态）"""
    s = current(tid=tid)
    new_s = on_ignored(s, hours)
    save(new_s, tid)
    if tid:
        g = current(tid=None)
        save(on_ignored(g, hours), None)
    return new_s


def remember_emotion(label, power=1.0, tid=None):
    """v18.11：记住当前情绪标签；voice.detect_emotion 优先读它"""
    if not label:
        return None
    s = dict(current(tid=tid))
    s["emotion"] = str(label)
    s["emotion_at"] = _time.time()
    s["emotion_power"] = max(0.0, min(1.0, float(power)))
    save(s, tid)
    return s


def emotion_power(tid=None):
    """当前情绪标签的剩余强度（0~1）"""
    s = current(tid=tid)
    return float(s.get("emotion_power") or 0.0) if s.get("emotion") else 0.0
