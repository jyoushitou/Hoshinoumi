# ===================== 突然想起（v18.12） =====================
# 每天最多一次：从 weight ≥ 0.7、7 天没提过的记忆里挑一条，
# 让她主动提起来。情绪低落时不提旧伤口。

import random
from datetime import datetime, timedelta

from ..config import CST, MASTER_QQ
from ..core import state as cfg
from ..log import log_api

MIN_WEIGHT = 0.7
GAP_DAYS = 7
SAD_MOOD = -0.3


def _parse_dt(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.strptime(str(value)[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def _when_word(days):
    if days < 14:
        return "上周"
    if days < 30:
        return "前阵子"
    return "之前"


def pick(tid=None, now=None):
    """挑一条可提的旧记忆；今天已经提过/心情差/没有候选就返回 None"""
    now = now or datetime.now(CST)
    if getattr(cfg, "recall_day", None) == now.date():
        return None

    try:
        from . import state as life_state
        mood = float((life_state.current(tid=tid) or {}).get("mood", 0.0))
        if mood < SAD_MOOD:
            log_api("[回忆] 心情差，跳过旧事")
            return None
    except Exception:
        pass

    try:
        from ..infra.repo_memory import load_heavy_memories
        rows = load_heavy_memories(tid or MASTER_QQ, MIN_WEIGHT, 20)
    except Exception:
        return None

    cutoff = now - timedelta(days=GAP_DAYS)
    eligible = []
    for row in rows or []:
        try:
            summary = row["summary"] if isinstance(row, dict) else row["summary"]
            last = _parse_dt(row["last_seen"]) or _parse_dt(row["created_at"])
        except Exception:
            continue
        if not summary:
            continue
        if last and last > cutoff:  # 最近提过，先不翻
            continue
        eligible.append((summary, last))
    if not eligible:
        return None

    summary, last = random.choice(eligible)
    days = max(0, (now - last).days) if last else 30
    when = _when_word(days)
    cfg.recall_day = now.date()
    log_api(f"[回忆] 今天提：{summary[:24]}")
    return {
        "summary": summary,
        "when": when,
        "prompt": (f"（你突然想起一件{when}的事：{summary}。"
                   f"顺口提一句，别像翻旧账，也别解释为什么想起来）"),
    }
