# ===================== Web/客户端提醒队列（v35.7.1.1） =====================
# 定时任务触发时入队；前端拉 pending，确认/稍后写回后端。
from __future__ import annotations

from datetime import datetime, timedelta

from .conn import get_cursor
from .schema import ensure_tables

TABLE = "reminders"


def _ensure():
    try:
        ensure_tables(names=[TABLE])
    except Exception:
        pass


def create(target_id: str, content: str, source_id: int | None = None, kind: str = "cron", user_id: str = "__owner__") -> int | None:
    _ensure()
    content = (content or "").strip()
    if not content:
        return None
    c = get_cursor()
    try:
        c.execute(
            "INSERT INTO reminders(user_id, target_id, source_id, kind, content, status) "
            "VALUES(%s,%s,%s,%s,%s,'pending')",
            (str(user_id), str(target_id), source_id, str(kind)[:16], content[:2000]),
        )
        return int(getattr(c, "lastrowid", 0) or 0)
    finally:
        try:
            c.close()
        except Exception:
            pass


def pending(user_id: str = "__owner__", limit: int = 20):
    _ensure()
    c = get_cursor()
    try:
        c.execute(
            "SELECT id, target_id, source_id, kind, content, created_at "
            "FROM reminders WHERE user_id=%s AND status='pending' "
            "AND (snooze_until IS NULL OR snooze_until<=CURRENT_TIMESTAMP) "
            "ORDER BY id DESC LIMIT %s",
            (str(user_id), max(1, min(int(limit), 50))),
        )
        return list(c.fetchall())
    finally:
        try:
            c.close()
        except Exception:
            pass


def ack(reminder_id: int, action: str, user_id: str = "__owner__", snooze_minutes: int = 10) -> bool:
    _ensure()
    action = str(action or "done").strip().lower()
    c = get_cursor()
    try:
        if action == "later":
            until = datetime.now() + timedelta(minutes=max(1, min(int(snooze_minutes), 1440)))
            c.execute(
                "UPDATE reminders SET status='pending', snooze_until=%s "
                "WHERE id=%s AND user_id=%s",
                (until, int(reminder_id), str(user_id)),
            )
        else:
            c.execute(
                "UPDATE reminders SET status='done', acked_at=CURRENT_TIMESTAMP "
                "WHERE id=%s AND user_id=%s",
                (int(reminder_id), str(user_id)),
            )
        return bool(getattr(c, "rowcount", 0))
    finally:
        try:
            c.close()
        except Exception:
            pass
