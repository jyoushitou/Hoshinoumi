# ===================== 本地阅读队列（v24.7） =====================
# data/books/ 的排队阅读：!book local <书名> 插到队首，空闲时按章读完。
# 队列持久化在 reading_queue；正文仍只在内存/本机文件，不入库。

from ..infra import tenant
from ..infra.conn import get_cursor


def _uid(user_id=None):
    return str(user_id or tenant.current_user_id())


def enqueue(user_id, name, total=0):
    uid = _uid(user_id)
    name = str(name)
    c = get_cursor()
    c.execute("SELECT position,last_chapter FROM reading_queue WHERE user_id=%s AND name=%s",
              (uid, name))
    row = c.fetchone()
    if row:
        new_pos = int(row["position"] or 0) - 1
        c.execute("UPDATE reading_queue SET position=%s,status='queued',total=%s "
                  "WHERE user_id=%s AND name=%s",
                  (new_pos, int(total or 0), uid, name))
    else:
        c.execute("SELECT MIN(position) AS p FROM reading_queue WHERE user_id=%s", (uid,))
        p = c.fetchone()
        pos = (int((p or {}).get("p") or 0) - 1)
        c.execute("INSERT INTO reading_queue(user_id,name,position,status,total) "
                  "VALUES(%s,%s,%s,'queued',%s)",
                  (uid, name, pos, int(total or 0)))
    c.connection.commit()
    return True


def list_queue(user_id=None):
    c = get_cursor()
    c.execute("SELECT name,position,status,last_chapter,total FROM reading_queue "
              "WHERE user_id=%s ORDER BY position", (_uid(user_id),))
    return list(c.fetchall() or [])


def active(user_id=None):
    c = get_cursor()
    c.execute("SELECT name,position,status,last_chapter,total FROM reading_queue "
              "WHERE user_id=%s AND status IN ('queued','reading') "
              "ORDER BY position LIMIT 1", (_uid(user_id),))
    return c.fetchone()


def get_item(user_id, name):
    c = get_cursor()
    c.execute("SELECT name,position,status,last_chapter,total FROM reading_queue "
              "WHERE user_id=%s AND name=%s", (_uid(user_id), str(name)))
    return c.fetchone()


def remove(user_id, name):
    c = get_cursor()
    c.execute("DELETE FROM reading_queue WHERE user_id=%s AND name=%s",
              (_uid(user_id), str(name)))
    c.connection.commit()
    return c.rowcount > 0


def set_progress(user_id, name, chapter, total=0, status="reading"):
    uid = _uid(user_id)
    total = int(total or 0)
    chapter = int(chapter or 0)
    if total and chapter >= total:
        status = "done"
    c = get_cursor()
    c.execute("UPDATE reading_queue SET last_chapter=%s,total=%s,status=%s "
              "WHERE user_id=%s AND name=%s",
              (chapter, total, status, uid, str(name)))
    c.connection.commit()


def mark_error(user_id, name):
    c = get_cursor()
    c.execute("UPDATE reading_queue SET status='error' WHERE user_id=%s AND name=%s",
              (_uid(user_id), str(name)))
    c.connection.commit()
