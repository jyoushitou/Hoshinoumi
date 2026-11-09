# ===================== 关系分档（v10-U8） =====================
# 亲密度 0~1，分四档，影响称呼和语气。
#
# 数值永远不进 prompt，只渲染成一句「你跟他什么关系」。

import json
import time as _time
from datetime import datetime

from ..config import CST
from ..log import log_system

# (下限, 档位名, 给模型看的一句话)
TIERS = [
    (0.70, "亲近", "他很亲近：可以损、可以损完再关心，但不必用力讨好"),
    (0.45, "熟", "算是熟人：可以开玩笑，但别太热络"),
    (0.20, "认识", "只是认识：礼貌、有距离，不主动交底"),
    (0.00, "陌生", "基本陌生：客气、简短，不透露自己的事"),
]

MASTER_START = 0.60      # 主人初始亲密度
DEFAULT_START = 0.10     # 陌生人
GAIN_PER_TALK = 0.005    # 每聊一轮 +0.005
DAILY_GAIN_CAP = 0.05    # 每天最多涨 0.05


def tier_of(affinity):
    """返回 (档位名, 描述)"""
    for lo, name, desc in TIERS:
        if affinity >= lo:
            return name, desc
    return "陌生", TIERS[-1][2]


def _today():
    return datetime.now(CST).strftime("%Y-%m-%d")


def get(tid):
    """读亲密度；没有就按身份给初始值"""
    from ..infra.repo_memory import load_relation
    from ..config import MASTER_QQ
    default = MASTER_START if str(tid) == str(MASTER_QQ) else DEFAULT_START
    try:
        raw = load_relation(str(tid))
        if not raw:
            return default
        data = json.loads(raw)
        return max(0.0, min(1.0, float(data.get("aff", default))))
    except Exception:
        return default


def _save(tid, affinity, gain_today, day):
    from ..infra.repo_memory import save_relation
    payload = json.dumps({"aff": round(affinity, 3), "gain": round(gain_today, 3), "day": day},
                         ensure_ascii=False, separators=(",", ":"))
    save_relation(str(tid), payload)


def bump(tid):
    """聊了一轮：涨一点亲密度（每天有上限，防止刷）"""
    tid = str(tid)
    aff = get(tid)
    day = _today()
    gain_today = 0.0
    try:
        from ..infra.repo_memory import load_relation
        raw = load_relation(tid)
        if raw:
            d = json.loads(raw)
            if d.get("day") == day:
                gain_today = float(d.get("gain", 0.0))
    except Exception:
        pass

    if gain_today >= DAILY_GAIN_CAP:
        return aff

    step = min(GAIN_PER_TALK, DAILY_GAIN_CAP - gain_today)
    aff = min(1.0, aff + step)
    try:
        _save(tid, aff, gain_today + step, day)
    except Exception as e:
        log_system(f"亲密度写入失败: {e}")
    return aff


def describe(tid):
    """给 prompt 用的一句关系描述（v12-G51：够熟才允许接半句）"""
    aff = get(tid)
    name, desc = tier_of(aff)
    extra = "（熟到可以把他没说完的话接下去，但别每次都猜）" if name in ("亲近", "熟") else ""
    return f"{desc}（现在是「{name}」）{extra}"
