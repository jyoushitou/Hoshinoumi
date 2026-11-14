# ===================== 定时任务存储与钩子（v17.6） =====================
# 表：cron_tasks（一人可以有多条）
# 钩子：每个任务一个 call_at，到点投递事件；触发后重新上膛。
#
# 这个模块只管「存」和「定时器」，不管「发什么」——
# 真正执行在 executors/cron.py（下一版做）。

import asyncio
from datetime import date, datetime, time as dt_time, timedelta

from ..log import log_api, log_err
from ..core import clock

# 一周从周一开始，和 Python 的 weekday() 差 1
_WEEK = {"mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 7}

handles = {}          # task_id -> TimerHandle
_prepare_handles = {} # v19.5：task_id -> 提前 30 秒预生成 TimerHandle
_generation = {}      # v21.7：task_id -> 代数；旧回调看到代数不匹配就退出
_prepare_generation = {}
_clock = {"now": None}  # 测试注入


def _uid(user_id):
    from ..infra import tenant
    return tenant.current_user_id() if user_id in (None, "", "__owner__") else str(user_id)


def _now():
    if _clock["now"]:
        return _clock["now"]()
    return clock.naive()


# ===================== 表操作 =====================

_COLS = ("id, user_id, target_id, schedule_type, at_time, weekdays, once_at, "
         "interval_min, content, source, enabled, jitter_min, last_fire, next_ts, "
         "rule, timing")


def list_tasks(target_id=None, enabled_only=False, user_id="__owner__"):
    user_id = _uid(user_id)
    from ..infra import cache
    from ..infra.conn import get_cursor

    key = f"cron:list:{user_id}:{target_id or ''}:{1 if enabled_only else 0}"
    hit = cache.get(key)
    if hit is not None:
        return list(hit)
    c = get_cursor()
    sql = f"SELECT {_COLS} FROM cron_tasks WHERE user_id=%s"
    params = [str(user_id)]
    if target_id:
        sql += " AND target_id=%s"
        params.append(str(target_id))
    if enabled_only:
        sql += " AND enabled=1"
    sql += " ORDER BY id"
    c.execute(sql, params or None)
    rows = list(c.fetchall())
    cache.set(key, rows, ttl=3.0)
    return rows


def get(task_id, user_id="__owner__"):
    user_id = _uid(user_id)
    from ..infra.conn import get_cursor

    c = get_cursor()
    c.execute(f"SELECT {_COLS} FROM cron_tasks WHERE id=%s AND user_id=%s",
                  (int(task_id), str(user_id)))
    return c.fetchone()


def add(target_id, schedule_type, content, at_time=None, weekdays=None,
        once_at=None, interval_min=None, source="command", jitter_min=10,
        rule=None, timing=None, user_id="__owner__"):
    user_id = _uid(user_id)
    """新增一条；返回新 id（失败返回 None）"""
    from ..infra.conn import get_cursor

    try:
        c = get_cursor()
        timing = timing or "exact"
        c.execute(
            "INSERT INTO cron_tasks(user_id, target_id, schedule_type, at_time, weekdays, "
            "once_at, interval_min, content, source, jitter_min, rule, timing) "
            "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (str(user_id), str(target_id), schedule_type, at_time, weekdays, once_at,
             interval_min, content, source, int(jitter_min), rule, timing))
        c.connection.commit()
        try:
            from ..infra import cache
            cache.invalidate("cron:list")
        except Exception:
            pass
        return c.lastrowid
    except Exception as e:
        log_err(f"[定时] 新增失败: {e}")
        return None


def remove(task_id, user_id="__owner__"):
    user_id = _uid(user_id)
    from ..infra.conn import get_cursor

    try:
        c = get_cursor()
        c.execute("DELETE FROM cron_tasks WHERE id=%s AND user_id=%s",
                  (int(task_id), str(user_id)))
        c.connection.commit()
        try:
            from ..infra import cache
            cache.invalidate("cron:list")
        except Exception:
            pass
        return True
    except Exception as e:
        log_err(f"[定时] 删除失败: {e}")
        return False


def set_enabled(task_id, on, user_id="__owner__"):
    user_id = _uid(user_id)
    from ..infra.conn import get_cursor

    try:
        c = get_cursor()
        c.execute("UPDATE cron_tasks SET enabled=%s WHERE id=%s AND user_id=%s",
                  (1 if on else 0, int(task_id), str(user_id)))
        c.connection.commit()
        try:
            from ..infra import cache
            cache.invalidate("cron:list")
        except Exception:
            pass
        return True
    except Exception as e:
        log_err(f"[定时] 启停失败: {e}")
        return False


def set_next(task_id, ts, user_id="__owner__"):
    user_id = _uid(user_id)
    from ..infra.conn import get_cursor

    try:
        c = get_cursor()
        c.execute("UPDATE cron_tasks SET next_ts=%s WHERE id=%s AND user_id=%s",
                  (ts, int(task_id), str(user_id)))
        c.connection.commit()
        try:
            from ..infra import cache
            cache.invalidate("cron:list")
        except Exception:
            pass
        return True
    except Exception:
        return False


# ===================== 算下次触发 =====================

def _is_workday(d):
    """法定工作日；没装 chinesecalendar 就退回周一到周五"""
    try:
        from chinesecalendar import is_workday
        return bool(is_workday(d))
    except Exception:
        return d.weekday() < 5


def _rule_time(rule, day):
    """v18.7：规则 → (时, 分)"""
    if rule == "wake":
        return (7, 30) if _is_workday(day) else (8, 0)
    if rule == "sleep":
        # 看「明天」是不是工作日
        return (23, 0) if _is_workday(day + timedelta(days=1)) else (23, 30)
    return None


def _parse_hm(text):
    text = (text or "").strip()
    if ":" not in text:
        return None
    try:
        hh, mm = int(text.split(":")[0]), int(text.split(":")[1])
    except (ValueError, IndexError):
        return None
    return (hh, mm) if 0 <= hh <= 23 and 0 <= mm <= 59 else None


def _timing_of(task):
    """exact / habit；老任务按 jitter_min 推断，保持兼容"""
    timing = (task.get("timing") or "").strip()
    if timing in ("exact", "habit"):
        return timing
    return "habit" if int(task.get("jitter_min") or 0) else "exact"


def _jittered(dt, task, rng):
    """exact 不抖；habit 只晚不早；老任务保留双向"""
    jitter = int(task.get("jitter_min") or 0)
    if jitter <= 0:
        return dt
    timing = _timing_of(task)
    if timing == "exact":
        return dt
    if timing == "habit":
        return dt + timedelta(minutes=rng.randint(0, jitter))
    return dt + timedelta(minutes=rng.randint(-jitter, jitter))


def _scene_of(task):
    content = (task.get("content") or "").strip()
    return content[6:].strip() if content.startswith("scene:") else content[:64]


def _override_for(task, day, use_overrides=True):
    """当天覆盖；查不到就 None（数据库异常也当没有）"""
    if not use_overrides or not task.get("target_id"):
        return None
    try:
        return get_override(task.get("target_id"), _scene_of(task), day)
    except Exception:
        return None


def compute_next(task, now=None, rng=None, use_overrides=True):
    """按任务类型算下一次时间；返回 datetime 或 None（已结束）"""
    import random

    now = now or _now()
    rng = rng or random
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
        return _jittered(last + timedelta(minutes=minutes), task, rng)

    rule = (task.get("rule") or "").strip()
    if rule not in ("wake", "sleep"):
        rule = ""

    # 规则任务（wake / sleep）：逐天算，覆盖优先
    if rule:
        for offset in range(0, 8):
            day = (now + timedelta(days=offset)).date()
            ov = _override_for(task, day, use_overrides)
            if ov and int(ov.get("skip") or 0):
                continue
            hm = _parse_hm(ov.get("at_time")) if ov and ov.get("at_time") else None
            hm = hm or _rule_time(rule, day)
            if not hm:
                continue
            cand = datetime.combine(day, dt_time(hm[0], hm[1]))
            if cand <= now:
                continue
            return _jittered(cand, task, rng)
        return None

    # fixed（daily / weekly）：原有逻辑 + 当天覆盖
    at = (task.get("at_time") or "").strip()
    hm = _parse_hm(at)
    if not hm:
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
        day = (now + timedelta(days=offset)).date()
        ov = _override_for(task, day, use_overrides)
        if ov and int(ov.get("skip") or 0):
            continue
        use_hm = _parse_hm(ov.get("at_time")) if ov and ov.get("at_time") else None
        use_hm = use_hm or hm
        cand = datetime.combine(day, dt_time(use_hm[0], use_hm[1]))
        if cand <= now:
            continue
        # 有覆盖就允许在非匹配星期触发（「今天 7:40 叫我」）
        if days is None or day.isoweekday() in days or (ov and ov.get("at_time")):
            return _jittered(cand, task, rng)
    return None


# ===================== 当天覆盖（v18.7） =====================
# cron_overrides：某个 target 的某个 scene 在某一天改成几点 / 跳过。
# 只影响那一天，第二天回规则。

def _day_str(day):
    return day.isoformat() if hasattr(day, "isoformat") else str(day)


def get_override(target_id, scene, day):
    from ..infra.conn import get_cursor

    c = get_cursor()
    c.execute(
        "SELECT at_time, skip FROM cron_overrides "
        "WHERE target_id=%s AND scene=%s AND day=%s",
        (str(target_id), str(scene), _day_str(day)))
    row = c.fetchone()
    if not row:
        return None
    try:
        return {"at_time": row["at_time"], "skip": int(row["skip"] or 0)}
    except Exception:
        return {"at_time": row[0], "skip": int(row[1] or 0)}


def add_override(target_id, scene, day, at_time=None, skip=False,
                 source="chat", note=""):
    """写当天覆盖（同一天同 scene 覆盖旧值）"""
    from ..infra.conn import get_cursor

    try:
        c = get_cursor()
        c.execute(
            "DELETE FROM cron_overrides WHERE target_id=%s AND scene=%s AND day=%s",
            (str(target_id), str(scene), _day_str(day)))
        c.execute(
            "INSERT INTO cron_overrides(target_id, scene, day, at_time, skip, source, note) "
            "VALUES(%s,%s,%s,%s,%s,%s,%s)",
            (str(target_id), str(scene), _day_str(day), at_time,
             1 if skip else 0, source, (note or "")[:200]))
        c.connection.commit()
        return True
    except Exception as e:
        log_err(f"[定时] 写当天覆盖失败: {e}")
        return False


def list_overrides(target_id=None, day=None):
    from ..infra.conn import get_cursor

    c = get_cursor()
    sql = ("SELECT id, target_id, scene, day, at_time, skip, source, note "
           "FROM cron_overrides WHERE 1=1")
    params = []
    if target_id:
        sql += " AND target_id=%s"
        params.append(str(target_id))
    if day:
        sql += " AND day=%s"
        params.append(_day_str(day))
    sql += " ORDER BY day, scene"
    c.execute(sql, params or None)
    return list(c.fetchall())


def clear_overrides(before_day=None):
    """清理过期覆盖；不传就清全部"""
    from ..infra.conn import get_cursor

    try:
        c = get_cursor()
        if before_day:
            c.execute("DELETE FROM cron_overrides WHERE day < %s", (_day_str(before_day),))
        else:
            c.execute("DELETE FROM cron_overrides")
        c.connection.commit()
        return True
    except Exception:
        return False


# ===================== 场景规则迁移（v18.7） =====================

_SCENE_RULES = {
    "scene:催起床": ("wake", "daily", None, None, "habit", 5),
    "scene:催睡觉": ("sleep", "daily", None, None, "habit", 3),
    "scene:提醒晚餐": (None, "daily", "16:40", None, "habit", 2),
    "scene:叮嘱午睡": (None, "daily", "12:30", None, "habit", 2),
    "scene:叫午睡起床": (None, "daily", "13:30", None, "exact", 0),
    "scene:提醒点外卖": (None, "daily", "10:40", None, "habit", 5),
    "scene:周日复盘": (None, "weekly", "21:00", "7", "exact", 0),
}


def migrate_scene_rules():
    """把 v17 的 8 条静态场景改成 v18.7 的规则（幂等）"""
    from ..infra.conn import get_cursor

    try:
        c = get_cursor()
        c.execute("DELETE FROM cron_tasks WHERE content='scene:周末吐槽赖床'")
        c.execute("UPDATE cron_tasks SET content='scene:叫午睡起床' "
                  "WHERE content='scene:提醒起身'")
        for content, (rule, stype, at, days, timing, jitter) in _SCENE_RULES.items():
            c.execute(
                "UPDATE cron_tasks SET rule=%s, schedule_type=%s, at_time=%s, "
                "weekdays=%s, timing=%s, jitter_min=%s, next_ts=NULL "
                "WHERE content=%s",
                (rule, stype, at, days, timing, int(jitter), content))
        c.connection.commit()
        try:
            from ..infra import cache
            cache.invalidate("cron:list")
        except Exception:
            pass
        return True
    except Exception as e:
        log_err(f"[定时] 场景规则迁移失败: {e}")
        return False


# ===================== 钩子管理 =====================

def _bump(task_id):
    _generation[task_id] = _generation.get(task_id, 0) + 1
    return _generation[task_id]


def _make_handle(task, loop, scheduler):
    task_id = int(task["id"])
    gen = _bump(task_id)
    nxt = compute_next(task)

    if nxt is None:
        log_api(f"[定时] 任务 {task_id} 没有下一次（一次性且已过期）")
        set_enabled(task_id, False)
        return None

    set_next(task_id, nxt)

    def _fire():
        if _generation.get(task_id) != gen:
            return  # 已被重排/取消，旧回调不再执行
        handles.pop(task_id, None)
        try:
            sched = scheduler
            if sched is None:
                # L15 修复：命令建的、启动对账建的钩子都没传 scheduler，
                # 以前这里直接跳过 → 到点什么都不做（静默失效）。
                from ..scheduler.dispatcher import get_scheduler

                sched = get_scheduler()
            sched.submit("cron_task", f"cron:{task_id}", args=(task_id,))
            log_api(f"[定时] 到点投递：任务 {task_id}")
        except Exception as e:
            log_err(f"[定时] 投递失败({task_id}): {e}")
        # 重新上膛
        try:
            fresh = get(task_id)
            if fresh and int(fresh.get("enabled") or 0):
                schedule_one(fresh, loop, scheduler)
        except Exception as e:
            log_err(f"[定时] 重排失败({task_id}): {e}")

    # v18.7：exact 任务提前 30 秒预生成，到点只发
    if _timing_of(task) == "exact":
        p_delay = (nxt - timedelta(seconds=30) - _now()).total_seconds()
        if p_delay > 0:
            def _fire_prepare():
                if _prepare_generation.get(task_id) != gen:
                    return
                _prepare_handles.pop(task_id, None)
                if task_id not in handles:
                    return
                try:
                    sched = scheduler
                    if sched is None:
                        from ..scheduler.dispatcher import get_scheduler
                        sched = get_scheduler()
                    sched.submit("cron_prepare", f"cronprep:{task_id}", args=(task_id,))
                except Exception as e:
                    log_err(f"[定时] 预生成投递失败({task_id}): {e}")
            _prepare_handles[task_id] = loop.call_at(loop.time() + p_delay, _fire_prepare)
            _prepare_generation[task_id] = gen

    handle = loop.call_at(
        loop.time() + max(0.0, (nxt - _now()).total_seconds()), _fire)
    handles[task_id] = handle
    return handle


def schedule_one(task, loop=None, scheduler=None):
    """给一条任务挂钩子（已有就先取消）"""
    cancel(int(task["id"]))
    if loop is None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            try:
                loop = asyncio.get_event_loop_policy().get_event_loop()
            except RuntimeError:
                log_err("[定时] 没有可用事件循环，钩子未挂载")
                return None
    return _make_handle(task, loop, scheduler)


def cancel(task_id):
    task_id = int(task_id)
    _bump(task_id)  # 让已排队的旧 prepare/fire 回调失效
    cancelled = False
    ph = _prepare_handles.pop(task_id, None)
    _prepare_generation.pop(task_id, None)
    if ph is not None:
        cancelled = True
        try:
            ph.cancel()
        except Exception:
            pass
    h = handles.pop(task_id, None)
    if h is not None:
        cancelled = True
        try:
            h.cancel()
        except Exception:
            pass
    return cancelled


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


def watchdog():
    """v18.7 U8：钩子丢了/时钟跳了 → 记错过并重排（不补发）"""
    now = _now()
    fixed = 0
    try:
        tasks = list_tasks(enabled_only=True)
    except Exception:
        return 0
    for t in tasks:
        try:
            tid = int(t.get("id"))
        except Exception:
            continue
        if tid in handles:
            continue
        nxt = t.get("next_ts")
        if isinstance(nxt, str):
            try:
                nxt = datetime.strptime(nxt, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                nxt = None
        if nxt and nxt <= now - timedelta(seconds=90):
            log_api(f"[定时] 钩子错过：任务 {tid}（计划 {nxt}），重排下一次")
            try:
                schedule_one(t)
                fixed += 1
            except Exception as e:
                log_err(f"[定时] 看门狗重排失败({tid}): {e}")
    try:  # 过期覆盖每天顺手清一次
        clear_overrides((now - timedelta(days=1)).date())
    except Exception:
        pass
    return fixed


def hook_rows():
    """v18.9：!hooks 用（任务 + 是否已挂 + 下次）"""
    try:
        tasks = list_tasks(enabled_only=True)
    except Exception:
        return []
    rows = []
    for t in tasks:
        try:
            tid = int(t.get("id"))
        except Exception:
            continue
        rows.append({
            "id": tid,
            "label": _scene_of(t) or (t.get("content") or "")[:20],
            "next": t.get("next_ts"),
            "hooked": tid in handles,
        })
    return rows


def next_summary():
    """v18.8：给 !stats 的一行：钩子数 + 最近一条"""
    try:
        tasks = list_tasks(enabled_only=True)
    except Exception:
        return "读取失败"
    now = _now()
    best = None
    for t in tasks:
        nxt = t.get("next_ts")
        if isinstance(nxt, str):
            try:
                nxt = datetime.strptime(nxt, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
        if not nxt or nxt <= now:
            continue
        if best is None or nxt < best[0]:
            best = (nxt, t)
    if not best:
        return f"钩子 {len(tasks)} 条｜下次 待排"
    nxt, task = best
    label = _scene_of(task) or (task.get("content") or "")[:20]
    return f"钩子 {len(tasks)} 条｜下次 {nxt.strftime('%m-%d %H:%M')}（{label}）"


def stats():
    return {
        "hooked": len(handles),
        "prepare": len(_prepare_handles),
        "ids": sorted(handles),
        "generations": dict(_generation),
    }
