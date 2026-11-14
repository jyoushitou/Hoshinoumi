# ===================== 关系分档（v23.4：-1.0 ~ 1.0） =====================
# 亲密度允许负值；下降由确定性事件触发，所有变化写 relation_events。
# 数值不进 prompt，只渲染成一句「你跟他什么关系」。

import json
import os
import random
from datetime import datetime

from ..config import CST
from ..log import log_system

OWNER = "__owner__"

# (下限, 档位名, 给模型看的一句话)
TIERS = [
    (0.70, "亲近", "他很亲近：可以损、可以损完再关心，但不必用力讨好"),
    (0.45, "熟", "算是熟人：可以开玩笑，但别太热络"),
    (0.20, "认识", "只是认识：礼貌、有距离，不主动交底"),
    (0.001, "陌生", "基本陌生：客气、简短，不透露自己的事"),
    (0.0, "归零", "关系归零：私聊回复概率最低，不再主动"),
    (-0.30, "冷淡", "关系冷淡：话短，减少主动，不交底"),
    (-0.60, "厌恶", "明显厌恶：拒绝亲近，语气带刺"),
    (-1.00, "破裂", "关系破裂：不主动、不交底，只保留基本功能"),
]

MASTER_START = 0.60
DEFAULT_START = 0.10
GAIN_PER_TALK = 0.005
DAILY_GAIN_CAP = 0.05
REPAIR_PER_DAY = 0.02
SEVERE_JUMP = 0.5
MIN_REPLY_PROB = float(os.getenv("NAO_MIN_REPLY_PROB", "0.01"))


def tier_of(affinity):
    for lo, name, desc in TIERS:
        if affinity >= lo:
            return name, desc
    return "破裂", TIERS[-1][2]


def _today():
    return datetime.now(CST).strftime("%Y-%m-%d")


def _clamp(v):
    return max(-1.0, min(1.0, float(v)))


def _raw(tid, user_id):
    from ..infra.repo_memory import load_relation
    if str(user_id) == OWNER:
        return load_relation(str(tid))
    return load_relation(str(tid), user_id=user_id)


def _save(tid, affinity, gain_today, day, user_id=OWNER):
    from ..infra.repo_memory import save_relation
    payload = json.dumps(
        {"aff": round(_clamp(affinity), 3), "gain": round(gain_today, 3), "day": day},
        ensure_ascii=False, separators=(",", ":"))
    if str(user_id) == OWNER:
        return save_relation(str(tid), payload)
    return save_relation(str(tid), payload, user_id=user_id)


def get(tid, user_id=OWNER):
    from ..config import MASTER_QQ
    default = MASTER_START if str(tid) == str(MASTER_QQ) else DEFAULT_START
    try:
        raw = _raw(tid, user_id)
        if not raw:
            return default
        data = json.loads(raw)
        return _clamp(float(data.get("aff", default)))
    except Exception:
        return default


def _get_compat(tid, user_id=OWNER):
    """旧测试会 monkeypatch get(tid)；owner 路径保持单参数兼容。"""
    if str(user_id) == OWNER:
        return get(tid)
    return get(tid, user_id=user_id)


def _log_event(tid, delta, reason, severity, user_id):
    try:
        from ..infra.conn import get_cursor
        c = get_cursor()
        c.execute(
            "INSERT INTO relation_events(user_id,target_id,delta,reason,severity) "
            "VALUES(%s,%s,%s,%s,%s)",
            (str(user_id), str(tid), round(float(delta), 3), str(reason)[:64],
             str(severity)[:16]))
        c.connection.commit()
    except Exception as e:
        log_system(f"[关系] 事件写入失败: {e}")


def apply_delta(tid, delta, reason, severity="minor", user_id=OWNER):
    """确定性扣分/加分；severity=major/severe 时可跳变，不受每日上涨上限保护。"""
    tid = str(tid)
    old = get(tid, user_id=user_id)
    new = _clamp(old + float(delta))
    day = _today()
    gain_today = 0.0
    try:
        data = json.loads(_raw(tid, user_id) or "{}")
        if data.get("day") == day:
            gain_today = float(data.get("gain", 0.0) or 0.0)
    except Exception:
        pass
    _save(tid, new, gain_today, day, user_id=user_id)
    if abs(delta) >= 0.001:
        _log_event(tid, delta, reason, severity, user_id)
        log_system(f"[关系] {tid} {old:+.3f} -> {new:+.3f}（{reason}）")
    return new


def bump(tid, user_id=OWNER):
    """普通聊天涨一点；负值/归零不靠聊天涨回来。"""
    tid = str(tid)
    aff = _get_compat(tid, user_id)
    if aff <= 0:
        return aff
    day = _today()
    gain_today = 0.0
    try:
        data = json.loads(_raw(tid, user_id) or "{}")
        if data.get("day") == day:
            gain_today = float(data.get("gain", 0.0) or 0.0)
    except Exception:
        pass
    if gain_today >= DAILY_GAIN_CAP:
        return aff
    step = min(GAIN_PER_TALK, DAILY_GAIN_CAP - gain_today)
    aff = _clamp(aff + step)
    try:
        _save(tid, aff, gain_today + step, day, user_id=user_id)
    except Exception as e:
        log_system(f"亲密度写入失败: {e}")
    return aff


def repair(tid, reason="道歉/持续修复", user_id=OWNER):
    """修复只能慢：每天最多 +0.02，不放宽上限。"""
    aff = _get_compat(tid, user_id)
    if aff >= 1.0:
        return aff
    return apply_delta(tid, REPAIR_PER_DAY, reason, "repair", user_id=user_id)


def reply_probability(tid, user_id=OWNER):
    aff = _get_compat(tid, user_id)
    if aff <= 0:
        return max(0.0, min(1.0, MIN_REPLY_PROB))
    if aff >= 0.70:
        return 1.0
    if aff >= 0.45:
        return 0.90
    if aff >= 0.20:
        return 0.70
    return 0.40


def should_answer_private(tid, text, user_id=OWNER, rng=None):
    """普通私聊回复 roll；道歉/求助不跳过。

    正值关系默认照常回复；只有归零/负值才启用最低概率，
    避免正常聊天被随机静默。
    """
    if any(w in (text or "") for w in ("对不起", "抱歉", "我错了", "帮我", "救命", "求助")):
        return True
    if _get_compat(tid, user_id) > 0:
        return True
    rng = rng or random
    return rng.random() < reply_probability(tid, user_id=user_id)


def recent_events(tid, user_id=OWNER, limit=5):
    try:
        from ..infra.conn import get_cursor
        c = get_cursor()
        c.execute(
            "SELECT delta,reason,severity,created_at FROM relation_events "
            "WHERE user_id=%s AND target_id=%s ORDER BY id DESC LIMIT %s",
            (str(user_id), str(tid), int(limit)))
        return list(c.fetchall() or [])
    except Exception:
        return []


def describe(tid, user_id=OWNER):
    aff = _get_compat(tid, user_id)
    name, desc = tier_of(aff)
    extra = "（熟到可以把他没说完的话接下去，但别每次都猜）" if name in ("亲近", "熟") else ""
    return f"{desc}（现在是「{name}」）{extra}"


ADDRESSING = {
    "亲近": "偶尔喊他「笨蛋」，损完记得收一句；别每句都喊",
    "熟": "正常叫「你」，偶尔直呼名字",
    "认识": "叫「你」，客气一点",
    "陌生": "叫「你」，别套近乎",
    "冷淡": "叫「你」，话短，别主动找话题",
    "厌恶": "少称呼，语气冷，不要亲近",
    "破裂": "只保留基本回应，不称呼、不交底",
}


def addressing(tid, user_id=OWNER):
    try:
        name, _desc = tier_of(_get_compat(tid, user_id))
    except Exception:
        return ""
    return ADDRESSING.get(name, "")
