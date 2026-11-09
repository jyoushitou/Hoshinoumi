# ===================== 读书流程（v16-U26/U27） =====================
# 空闲时读几章 → 记进度 → 之后聊天能提。
#
# 存储：events(kind='reading')，一人一行 JSON：
#   {"books": [{"title","url","last_no","last_title","intro"}],
#    "day": "2026-11-09", "chapters": 3}

import json
import os
from datetime import datetime

from ..config import CST
from ..log import log_api, log_system

IDLE_HOURS = float(os.getenv("NAO_READ_IDLE_HOURS", "2"))
DAILY_CHAPTERS = int(os.getenv("NAO_READ_DAILY_CHAPTERS", "20"))
MAX_PER_SESSION = 3
NIGHT_START, NIGHT_END = 1, 7        # 深夜不读
SHARE_PROB = 0.20                    # 读完一章说一句的概率
SUMMARY_MAX = 100


def _now(now=None):
    return now or datetime.now(CST)


def _today_str(now=None):
    return _now(now).strftime("%Y-%m-%d")


# ===================== 存取 =====================

def load(tid):
    try:
        from ..infra.repo_memory import load_reading
        raw = load_reading(str(tid))
        data = json.loads(raw) if raw else {}
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("books", [])
    data.setdefault("day", "")
    data.setdefault("chapters", 0)
    return data


def save(tid, data):
    try:
        from ..infra.repo_memory import save_reading
        save_reading(str(tid), json.dumps(data, ensure_ascii=False, separators=(",", ":")))
        return True
    except Exception:
        return False


# ===================== 节奏控制 =====================

def is_night(now=None):
    hour = _now(now).hour
    return NIGHT_START <= hour < NIGHT_END


def quota_left(data, now=None):
    """今天还能读几章"""
    if data.get("day") != _today_str(now):
        return DAILY_CHAPTERS
    return max(0, DAILY_CHAPTERS - int(data.get("chapters", 0) or 0))


def mark_read(data, count=1, now=None):
    """记一次读书（跨天自动清零）"""
    today = _today_str(now)
    if data.get("day") != today:
        data["day"] = today
        data["chapters"] = 0
    data["chapters"] = int(data.get("chapters", 0) or 0) + max(0, count)
    return data


def is_idle(last_user_ts, now=None):
    """主人多久没说话了"""
    if not last_user_ts:
        return True
    return (_now(now).timestamp() - last_user_ts) >= IDLE_HOURS * 3600


def should_read(last_user_ts=None, now=None):
    """现在能不能读：不在深夜 + 主人闲着"""
    if is_night(now):
        return False, "深夜"
    if not is_idle(last_user_ts, now):
        return False, "刚聊过"
    return True, "ok"


# ===================== 书籍与进度 =====================

def current_book(data):
    books = data.get("books") or []
    return books[-1] if books else None


def next_chapters(chapters, last_no, limit=MAX_PER_SESSION):
    """从目录里挑下一批；last_no 之后的前几章"""
    if not chapters:
        return []
    pending = [(t, u) for t, u in chapters if _chapter_no(t) > last_no]
    return pending[:limit]


def _chapter_no(title):
    from .novel import chapter_no
    return chapter_no(title)


def update_progress(data, title, url, chapter_title, intro=""):
    """推进一本书的进度"""
    books = data.setdefault("books", [])
    no = _chapter_no(chapter_title)
    for b in books:
        if b.get("url") == url:
            b["last_no"] = max(int(b.get("last_no", 0) or 0), no)
            b["last_title"] = chapter_title
            b["title"] = b.get("title") or title
            if intro and not b.get("intro"):
                b["intro"] = intro[:200]
            return b
    book = {"title": title, "url": url, "last_no": no,
            "last_title": chapter_title, "intro": (intro or "")[:200]}
    books.append(book)
    return book


def describe(tid):
    """给 prompt 用：她在看什么"""
    data = load(tid)
    book = current_book(data)
    if not book:
        return ""
    line = f"你在看《{book.get('title', '')}》"
    if book.get("last_no"):
        line += f"，看到第 {book['last_no']} 章"
    return line


# ===================== 读一次 =====================

async def read_once(tid, fetch_book=None, fetch_chapter=None, summarize=None, now=None):
    """读一章（或几章）。依赖注入方便测试。

    返回 {"ok": bool, "chapter": str, "summary": str, "reason": str}
    """
    ok, why = should_read(None, now)
    if not ok:
        return {"ok": False, "reason": why}

    data = load(tid)
    if quota_left(data, now) <= 0:
        return {"ok": False, "reason": "今天读够了"}
    book = current_book(data)
    if not book:
        return {"ok": False, "reason": "还没挑书"}

    try:
        info = await fetch_book(book["url"]) if fetch_book else None
    except Exception as e:
        log_api(f"[读书] 取目录失败: {e}")
        info = None
    if not info or not info.get("chapters"):
        return {"ok": False, "reason": "目录取不到"}

    batch = next_chapters(info["chapters"], int(book.get("last_no", 0) or 0), 1)
    if not batch:
        return {"ok": False, "reason": "没有新章节"}

    chapter_title, chapter_url = batch[0]
    try:
        text = await fetch_chapter(chapter_url) if fetch_chapter else ""
    except Exception as e:
        log_api(f"[读书] 取正文失败: {e}")
        text = ""
    if not text:
        return {"ok": False, "reason": "正文取不到"}

    summary = ""
    if summarize:
        try:
            summary = await summarize(text[:3000]) or ""
        except Exception as e:
            log_api(f"[读书] 摘要失败: {e}")
    summary = (summary or "").strip()[:SUMMARY_MAX]

    update_progress(data, info.get("title") or book.get("title", ""),
                    book["url"], chapter_title, info.get("intro", ""))
    mark_read(data, 1, now)
    save(tid, data)
    log_system(f"读书: {data['books'][-1]['title']} {chapter_title}（摘要 {len(summary)} 字）")
    return {"ok": True, "chapter": chapter_title, "summary": summary, "reason": "ok"}
