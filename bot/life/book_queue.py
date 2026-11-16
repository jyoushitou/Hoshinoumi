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
        c.execute("UPDATE reading_queue SET position=%s,status='queued',"
                  "last_chapter=0,char_offset=0,total=%s "
                  "WHERE user_id=%s AND name=%s",
                  (new_pos, int(total or 0), uid, name))
    else:
        c.execute("SELECT MIN(position) AS p FROM reading_queue WHERE user_id=%s", (uid,))
        p = c.fetchone()
        pos = (int((p or {}).get("p") or 0) - 1)
        c.execute("INSERT INTO reading_queue(user_id,name,position,status,total,char_offset) "
                  "VALUES(%s,%s,%s,'queued',%s,0)",
                  (uid, name, pos, int(total or 0)))
    c.connection.commit()
    return True


def list_queue(user_id=None):
    uid = _uid(user_id)
    c = get_cursor()
    c.execute("SELECT name,position,status,last_chapter,char_offset,total FROM reading_queue "
              "WHERE user_id=%s ORDER BY position", (uid,))
    rows = list(c.fetchall() or [])
    # v28.9：修复旧版本把首段 1000 字误标 done 的行
    for row in rows:
        if row.get("status") == "done":
            repair_done(uid, row.get("name"))
    c.execute("SELECT name,position,status,last_chapter,char_offset,total FROM reading_queue "
              "WHERE user_id=%s ORDER BY position", (uid,))
    return list(c.fetchall() or [])


def active(user_id=None):
    uid = _uid(user_id)
    c = get_cursor()
    sql = ("SELECT name,position,status,last_chapter,char_offset,total FROM reading_queue "
           "WHERE user_id=%s AND status IN ('queued','reading') "
           "ORDER BY position LIMIT 1")
    c.execute(sql, (uid,))
    row = c.fetchone()
    if row:
        return row
    # v28.9：旧版本把首段误标 done 后，active() 看不到它；
    # 空闲 tick 会误以为没有本地队列。先修复再重查。
    c.execute("SELECT name FROM reading_queue WHERE user_id=%s AND status='done'", (uid,))
    names = [r["name"] for r in (c.fetchall() or [])]
    for name in names:
        repair_done(uid, name)
    if names:
        c.execute(sql, (uid,))
        return c.fetchone()
    return None


def get_item(user_id, name):
    c = get_cursor()
    c.execute("SELECT name,position,status,last_chapter,char_offset,total FROM reading_queue "
              "WHERE user_id=%s AND name=%s", (_uid(user_id), str(name)))
    return c.fetchone()


def remove(user_id, name):
    c = get_cursor()
    c.execute("DELETE FROM reading_queue WHERE user_id=%s AND name=%s",
              (_uid(user_id), str(name)))
    c.connection.commit()
    return c.rowcount > 0


def set_total(user_id, name, total):
    c = get_cursor()
    c.execute("UPDATE reading_queue SET total=%s WHERE user_id=%s AND name=%s",
              (int(total or 0), _uid(user_id), str(name)))
    c.connection.commit()


def set_progress(user_id, name, chapter, total=0, status=None, offset=0):
    uid = _uid(user_id)
    total = int(total or 0)
    chapter = int(chapter or 0)
    # v28.9：显式 status 由 read_chunk 的 done 决定，绝不再用章节数强制 done。
    # 旧调用（不传 status）保留 chapter>=total 的行为。
    if status is None:
        status = "done" if (total and chapter >= total) else "reading"
    c = get_cursor()
    c.execute("UPDATE reading_queue SET last_chapter=%s,char_offset=%s,total=%s,status=%s "
              "WHERE user_id=%s AND name=%s",
              (chapter, int(offset or 0), total, status, uid, str(name)))
    c.connection.commit()


def repair_done(user_id, name):
    """把“done 但实际没读完”的历史行改回 reading；真正读完的保持 done。"""
    item = get_item(user_id, name)
    if not item or item.get("status") != "done":
        return False
    try:
        from .local_books import load_book, _chapter_layout
        _title, chapters = load_book(item["name"])
        _starts, total_chars = _chapter_layout(chapters)
    except Exception:
        return False
    if int(item.get("char_offset") or 0) < int(total_chars or 0):
        c = get_cursor()
        c.execute("UPDATE reading_queue SET status='reading' "
                  "WHERE user_id=%s AND name=%s", (_uid(user_id), item["name"]))
        c.connection.commit()
        return True
    return False


def mark_error(user_id, name):
    c = get_cursor()
    c.execute("UPDATE reading_queue SET status='error' WHERE user_id=%s AND name=%s",
              (_uid(user_id), str(name)))
    c.connection.commit()
