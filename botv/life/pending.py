# ===================== 待办与时间锚点（v10-U9b） =====================
# 她说「回头再说」，隔天要真的来问；
# 你说「我去吃饭」，二十几分钟后她要问一句「完了？」。
#
# 存储：events 表里 kind='agenda' 的行，一行一条，__self__ 名下。

import json
import re
import time as _time
from datetime import datetime

from ..config import CST
from ..log import log_system

# 承诺类：说了这些，隔天要回访
PROMISE_PATTERNS = [
    "回头再说", "回头聊", "回头找你", "晚点聊", "晚点说", "改天聊", "改天再说",
    "下次再聊", "等会儿说", "先不聊了", "先这样", "我先忙",
]

# 时间锚点：去做什么，多久之后问一句
ANCHOR_PATTERNS = [
    (("去吃饭", "吃饭去", "先吃饭"), 30, "吃饭"),
    (("去洗澡", "洗澡去", "先洗澡"), 25, "洗澡"),
    (("去开会", "开会去", "有个会"), 40, "开会"),
    (("去上课", "上课去"), 60, "上课"),
]

PROMISE_DELAY_HOURS = 20      # 承诺类：20 小时后回访
EXPIRE_HOURS = 30             # 超过 30 小时没处理就作废
MAX_ITEMS = 5


def _now_ts(now=None):
    return (now or datetime.now(CST)).timestamp()


def detect(text, now=None):
    """从一句话里识别出该记的待办，返回 [item, ...]"""
    text = (text or "").strip()
    if not text:
        return []
    now_ts = _now_ts(now)
    items = []

    for kw in PROMISE_PATTERNS:
        if kw in text:
            items.append({
                "k": "promise",
                "due": now_ts + PROMISE_DELAY_HOURS * 3600,
                "t": "你之前提到的那件事",
                "s": text[:40],
            })
            break

    for words, minutes, label in ANCHOR_PATTERNS:
        if any(w in text for w in words):
            items.append({
                "k": "anchor",
                "due": now_ts + minutes * 60,
                "t": label,
                "s": text[:40],
            })
            break

    return items


def add(items):
    """把待办写库；写入失败就当没记（不影响回复）"""
    if not items:
        return 0
    try:
        from ..infra.repo_memory import add_event_to_db, STATE_TARGET
        for it in items[:MAX_ITEMS]:
            add_event_to_db(STATE_TARGET, json.dumps(it, ensure_ascii=False),
                            tags="待办", kind="agenda")
        return len(items)
    except Exception as e:
        log_system(f"待办写入失败: {e}")
        return 0


def due(now=None):
    """取出到点的待办，并清理过期的"""
    from ..infra.repo_memory import load_agenda_items, delete_agenda_item
    now_ts = _now_ts(now)
    ready, expired = [], []
    try:
        rows = load_agenda_items()
    except Exception:
        return []
    for row in rows:
        try:
            it = json.loads(row["event_summary"] or "{}")
        except Exception:
            expired.append(row["id"])
            continue
        if now_ts - float(it.get("due", 0)) > EXPIRE_HOURS * 3600:
            expired.append(row["id"])
        elif float(it.get("due", 0)) <= now_ts:
            ready.append((row["id"], it))
    for rid in expired:
        try:
            delete_agenda_item(rid)
        except Exception:
            pass
    return ready


def finish(item_id):
    """处理完删掉"""
    try:
        from ..infra.repo_memory import delete_agenda_item
        delete_agenda_item(item_id)
    except Exception:
        pass


def describe(item):
    """给 prompt 用的一句提示"""
    kind = item.get("k")
    if kind == "promise":
        return f"你之前答应过要问一句的事（对方说过：{item.get('s', '')}）"
    return f"对方说到要去{item.get('t', '忙')}，现在该问一句了（原话：{item.get('s', '')}）"
