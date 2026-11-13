# ===================== 日程 / 待办的秒级钩子（v18.7） =====================
# 到点直接 loop.call_at；不再让 minute_tick 每 30 秒扫 process_due。
#
# 进程重启后由 schedule_all() 从 events 表重建；过期项不补发。

import asyncio
import json
import time

from ..log import log_api, log_err

_handles = {}   # (kind, item_id) -> TimerHandle


def _key(kind, item_id):
    return f"{kind}:{item_id}"


def cancel(kind, item_id):
    h = _handles.pop(_key(kind, item_id), None)
    if h is not None:
        try:
            h.cancel()
        except Exception:
            pass
        return True
    return False


def schedule(kind, item_id, due_ts, text, only_missing=False):
    """挂一个到点钩子；due_ts 是 epoch 秒。only_missing=True 时不重排已有钩子"""
    key = _key(kind, item_id)
    if only_missing and key in _handles:
        return _handles[key]
    cancel(kind, item_id)
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return None
    delay = max(0.0, float(due_ts or 0) - time.time())
    handle = loop.call_at(loop.time() + delay, _fire, kind, item_id, text)
    _handles[_key(kind, item_id)] = handle
    return handle


def _fire(kind, item_id, text):
    _handles.pop(_key(kind, item_id), None)
    try:
        from ..scheduler.dispatcher import get_scheduler
        sched = get_scheduler()
        if kind == "agenda":
            sched.submit("agenda_remind", f"agenda:{item_id}", args=(text, item_id))
        else:
            sched.submit("pending_nudge", f"pending:{item_id}", args=(text, item_id))
        log_api(f"[{kind}] 到点投递：{item_id}")
    except Exception as e:
        log_err(f"[{kind}] 投递失败({item_id}): {e}")


def schedule_all(only_missing=False):
    """启动/04:00 对账：从 events 表重建未到点的日程/待办"""
    n = 0
    try:
        from ..life.agenda import list_all as agenda_all
        for it in agenda_all():
            if it.get("d"):
                continue
            due = float(it.get("due") or 0)
            if due <= time.time():
                continue
            if schedule("agenda", it.get("id"), due, it.get("t", ""), only_missing=only_missing):
                n += 1
    except Exception as e:
        log_err(f"[agenda] 重建失败: {e}")

    try:
        from ..infra.repo_memory import load_agenda_items
        from ..life.pending import describe as describe_pending
        for row in load_agenda_items():
            try:
                it = json.loads(row["event_summary"] or "{}")
            except Exception:
                continue
            due = float(it.get("due") or 0)
            if due <= time.time():
                continue
            if schedule("pending", row["id"], due, describe_pending(it), only_missing=only_missing):
                n += 1
    except Exception as e:
        log_err(f"[pending] 重建失败: {e}")
    return n


def watchdog():
    """v19.5：只补缺失钩子，不重排已有日程/待办"""
    return schedule_all(only_missing=True)


def stats():
    return {"hooked": len(_handles), "keys": sorted(_handles)}
