# ===================== 定时任务存储与钩子（v17.6） =====================
# 表：cron_tasks（一人可以有多条）
# 钩子：每个任务一个 call_at，到点投递事件；触发后重新上膛。
#
# 这个模块只管「存」和「定时器」，不管「发什么」——
# 真正执行在 executors/cron.py（下一版做）。

import asyncio
from datetime import datetime, timedelta

from ..log import log_api, log_err

# 一周从周一开始，和 Python 的 weekday() 差 1
_WEEK = {"mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 7}

handles = {}          # task_id -> TimerHandle
_clock = {"now": None}  # 测试注入


def _now():
    if _clock["now"]:
        return _clock["now"]()
    return datetime.now()


# ===================== 表操作 =====================

_COLS = ("id, target_id, schedule_type, at_time, weekdays, once_at, "
         "interval_min, content, source, enabled, jitter_min, last_fire, next_ts")


def list_tasks(target_id=None, enabled_only=False):
    from ..infra.conn import get_cursor

    c = get_cursor()
    sql = f"SELECT {_COLS} FROM cron_tasks WHERE 1=1"
    params = []
    if target_id:
        sql += " AND target_id=%s"
        params.append(str(target_id))
    if enabled_only:
        sql += " AND enabled=1"
    sql += " ORDER BY id"
    c.execute(sql, params or None)
    return list(c.fetchall())


def get(task_id):
    from ..infra.conn import get_cursor

    c = get_cursor()
    c.execute(f"SELECT {_COLS} FROM cron_tasks WHERE id=%s", (int(task_id),))
    return c.fetchone()


def add(target_id, schedule_type, content, at_time=None, weekdays=None,
        once_at=None, interval_min=None, source="command", jitter_min=10):
    """新增一条；返回新 id（失败返回 None）"""
    from ..infra.conn import get_cursor

    try:
        c = get_cursor()
        c.execute(
            "INSERT INTO cron_tasks(target_id, schedule_type, at_time, weekdays, "
            "once_at, interval_min, content, source, jitter_min) "
            "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (str(target_id), schedule_type, at_time, weekdays, once_at,
             interval_min, content, source, int(jitter_min)))
        c.connection.commit()
        return c.lastrowid
    except Exception as e:
        log_err(f"[定时] 新增失败: {e}")
        return None


def remove(task_id):
    from ..infra.conn import get_cursor

    try:
        c = get_cursor()
        c.execute("DELETE FROM cron_tasks WHERE id=%s", (int(task_id),))
        c.connection.commit()
        return True
    except Exception as e:
        log_err(f"[定时] 删除失败: {e}")
        return False


def set_enabled(task_id, on):
    from ..infra.conn import get_cursor

    try:
        c = get_cursor()
        c.execute("UPDATE cron_tasks SET enabled=%s WHERE id=%s",
                  (1 if on else 0, int(task_id)))
        c.connection.commit()
        return True
    except Exception as e:
        log_err(f"[定时] 启停失败: {e}")
        return False


def set_next(task_id, ts):
    from ..infra.conn import get_cursor

    try:
        c = get_cursor()
        c.execute("UPDATE cron_tasks SET next_ts=%s WHERE id=%s", (ts, int(task_id)))
        c.connection.commit()
        return True
    except Exception:
        return False


# ===================== 算下次触发 =====================

def compute_next(task, now=None, rng=None):
    """按任务类型算下一次时间；返回 datetime 或 None（已结束）"""
    import random

    now = now or _now()
    rng = rng or random
    jitter = int(task.get("jitter_min") or 0)

    def jittered(dt):
        if not jitter:
            return dt
        return dt + timedelta(minutes=rng.randint(-jitter, jitter))

    stype = task.get("schedule_type")

    if stype == "once":
        once_at = task.get("once_at")
        if not once_at:
            return None
        if isinstance(once_at, str):
            try:
                once_at = datetime.strptime(once_at, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    once_at = datetime.strptime(once_at, "%Y-%m-%d %H:%M")
                except ValueError:
                    return None
        return once_at if once_at > now else None

    if stype == "interval":
        minutes = int(task.get("interval_min") or 0)
        if minutes <= 0:
            return None
        last = task.get("last_fire") or now
        if isinstance(last, str):
            try:
                last = datetime.strptime(last, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                last = now
        return jittered(last + timedelta(minutes=minutes))

    # daily / weekly：从「明天」开始找第一个匹配的日期
    at = (task.get("at_time") or "").strip()
    if ":" not in at:
        return None                      # 没有时间就不排
    try:
        hh, mm = int(at.split(":")[0]), int(at.split(":")[1])
    except (ValueError, IndexError):
        return None
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        return None

    days = None
    if stype == "weekly":
        raw = (task.get("weekdays") or "").replace(" ", "")
        days = set()
        for part in raw.split(","):
            if not part:
                continue
            if part.isdigit():
                days.add(int(part))
            elif part[:3].lower() in _WEEK:
                days.add(_WEEK[part[:3].lower()])
        if not days:
            return None

    for offset in range(0, 8):
        day = (now + timedelta(days=offset)).replace(hour=hh, minute=mm,
                                                    second=0, microsecond=0)
        if day <= now:
            continue
        if days is None or day.isoweekday() in days:
            return jittered(day)
    return None


# ===================== 钩子管理 =====================

def _make_handle(task, loop, scheduler):
    task_id = int(task["id"])
    nxt = compute_next(task)

    if nxt is None:
        log_api(f"[定时] 任务 {task_id} 没有下一次（一次性且已过期）")
        set_enabled(task_id, False)
        return None

    set_next(task_id, nxt)

    def _fire():
        handles.pop(task_id, None)
        try:
            if scheduler is not None:
                scheduler.submit("cron_task", f"cron:{task_id}",
                                 args=(task_id,))
        except Exception as e:
            log_err(f"[定时] 投递失败({task_id}): {e}")
        # 重新上膛
        try:
            fresh = get(task_id)
            if fresh and int(fresh.get("enabled") or 0):
                schedule_one(fresh, loop, scheduler)
        except Exception as e:
            log_err(f"[定时] 重排失败({task_id}): {e}")

    handle = loop.call_at(
        loop.time() + max(0.0, (nxt - _now()).total_seconds()), _fire)
    handles[task_id] = handle
    return handle


def schedule_one(task, loop=None, scheduler=None):
    """给一条任务挂钩子（已有就先取消）"""
    cancel(int(task["id"]))
    loop = loop or asyncio.get_event_loop()
    return _make_handle(task, loop, scheduler)


def cancel(task_id):
    h = handles.pop(int(task_id), None)
    if h is not None:
        try:
            h.cancel()
        except Exception:
            pass
        return True
    return False


def cancel_all():
    for tid in list(handles):
        cancel(tid)


def schedule_all(tasks=None, loop=None, scheduler=None):
    """全量重建（启动 / 04:00 对账用）"""
    tasks = tasks if tasks is not None else list_tasks(enabled_only=True)
    cancel_all()
    n = 0
    for t in tasks:
        try:
            if schedule_one(t, loop, scheduler):
                n += 1
        except Exception as e:
            log_err(f"[定时] 挂载失败({t.get('id')}): {e}")
    log_api(f"[定时] 钩子已重建：{n} 条")
    return n


def stats():
    return {"hooked": len(handles), "ids": sorted(handles)}
