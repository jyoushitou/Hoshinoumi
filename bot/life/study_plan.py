# ===================== 学习规划领域逻辑（v34） =====================

import json
from datetime import date, datetime, timedelta

DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
STATUSES = {"todo", "done", "skipped", "moved"}
KINDS = {"study", "review", "practice", "exam", "ddl", "life", "other"}


def monday_of(value):
    if isinstance(value, datetime):
        d = value.date()
    elif isinstance(value, date):
        d = value
    else:
        d = date.fromisoformat(str(value)[:10])
    return d - timedelta(days=d.weekday())


def validate_cell(cell, idx=0):
    if not isinstance(cell, dict):
        raise ValueError(f"{DAYS[idx]} 第 {idx} 项必须是对象")
    no = cell.get("no")
    if no is None:
        cell["no"] = idx + 1
    elif not isinstance(no, int) or no < 1:
        raise ValueError("no 必须是正整数")
    t = str(cell.get("time") or "")
    if t:
        try:
            h, m = t.split(":")
            if not (0 <= int(h) <= 23 and 0 <= int(m) <= 59):
                raise ValueError
        except Exception:
            raise ValueError(f"非法时间: {t}")
    status = cell.get("status") or "todo"
    if status not in STATUSES:
        raise ValueError(f"非法状态: {status}")
    cell["status"] = status
    kind = cell.get("kind") or "study"
    if kind not in KINDS:
        kind = "other"
    cell["kind"] = kind
    cell.setdefault("subject", "")
    cell.setdefault("task", "")
    cell.setdefault("estimate_min", 0)
    cell.setdefault("actual_min", 0)
    cell.setdefault("note", "")
    cell.setdefault("notified_at", None)
    return cell


def validate_plan(data):
    if not isinstance(data, dict):
        raise ValueError("计划必须是对象")
    week = monday_of(data.get("week_start") or date.today())
    out = {"week_start": week.isoformat(), "title": str(data.get("title") or "")[:128]}
    for i, day in enumerate(DAYS):
        rows = data.get(day) or []
        if not isinstance(rows, list):
            raise ValueError(f"{day} 必须是数组")
        seen = set()
        out[day] = []
        for j, cell in enumerate(rows):
            c = validate_cell(dict(cell), j)
            if c["no"] in seen:
                raise ValueError(f"{day} no 重复: {c['no']}")
            seen.add(c["no"])
            out[day].append(c)
    return out


def empty_week(value):
    week = monday_of(value)
    data = {"week_start": week.isoformat(), "title": ""}
    for day in DAYS:
        data[day] = []
    return data


def dumps(data):
    return json.dumps(validate_plan(data), ensure_ascii=False)


def loads(text):
    return validate_plan(json.loads(text))


def _row_to_plan(row):
    data = {"week_start": str(row["week_start"])[:10], "title": row.get("title") or ""}
    for day in DAYS:
        raw = row.get(day)
        try:
            data[day] = json.loads(raw) if raw else []
        except Exception:
            data[day] = []
    return validate_plan(data)


def load_week(user_id, week_start):
    from ..infra.conn import get_cursor
    week = monday_of(week_start).isoformat()
    c = get_cursor()
    try:
        c.execute("SELECT * FROM study_plans WHERE user_id=%s AND week_start=%s",
                  (str(user_id), week))
        row = c.fetchone()
        return _row_to_plan(row) if row else empty_week(week)
    finally:
        try: c.close()
        except Exception: pass


def save_week(user_id, data):
    plan = validate_plan(data)
    from ..infra.conn import get_cursor
    c = get_cursor()
    vals = [json.dumps(plan[d], ensure_ascii=False) for d in DAYS]
    try:
        c.execute("UPDATE study_plans SET title=%s, monday=%s, tuesday=%s, "
                  "wednesday=%s, thursday=%s, friday=%s, saturday=%s, sunday=%s "
                  "WHERE user_id=%s AND week_start=%s",
                  [plan.get("title", "")] + vals + [str(user_id), plan["week_start"]])
        if not getattr(c, "rowcount", 0):
            c.execute("INSERT INTO study_plans(user_id, week_start, title, monday, tuesday, "
                      "wednesday, thursday, friday, saturday, sunday) "
                      "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                      [str(user_id), plan["week_start"], plan.get("title", "")] + vals)
        c.connection.commit()
        return plan
    finally:
        try: c.close()
        except Exception: pass


def import_text(user_id, text):
    return save_week(user_id, json.loads(text))


def export_text(user_id, week_start):
    return json.dumps(load_week(user_id, week_start), ensure_ascii=False, indent=2)


def format_day(plan, day, limit=20):
    rows = plan.get(day) or []
    if not rows:
        return "今天没有安排。"
    lines = [f"📅 {day}："]
    for c in rows[:limit]:
        mark = {"done": "✅", "skipped": "⏭️", "moved": "↪️"}.get(c.get("status"), "·")
        t = c.get("time") or "--:--"
        lines.append(f"  {mark} {t} {c.get('subject','')} {c.get('task','')}".rstrip())
    return "\n".join(lines)


def format_week(plan):
    start = plan.get("week_start", "")
    lines = [f"📋 学习计划 {start}"]
    for day in DAYS:
        rows = plan.get(day) or []
        if not rows:
            continue
        lines.append("")
        lines.append(day)
        for c in rows:
            mark = {"done": "✅", "skipped": "⏭️", "moved": "↪️"}.get(c.get("status"), "·")
            lines.append(f"  {mark} {c.get('time') or '--:--'} {c.get('subject','')} {c.get('task','')}".rstrip())
    return "\n".join(lines)


def set_status(user_id, week_start, day, no, status):
    plan = load_week(user_id, week_start)
    for c in plan.get(day, []):
        if int(c.get("no", 0)) == int(no):
            c["status"] = status
            save_week(user_id, plan)
            return c
    return None
