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
    except Exception as e:
        log_api(f"[读书] 保存进度失败 tid={tid}: {e}")  # 别静默吞掉
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


# ===================== 挑书 =====================

# 起步书单：番茄的公开书籍页（可被 NAO_BOOK_URLS 覆盖）
DEFAULT_BOOKS = [
    ("天外玉", "https://fanqienovel.com/page/7688347825909812248"),
    ("莫若凌霄", "https://fanqienovel.com/page/7091150316644600867"),
    ("惊鸿", "https://fanqienovel.com/page/6883748331202284558"),
]


def book_candidates():
    """书单：环境变量 NAO_BOOK_URLS（逗号分隔的「名字|url」）优先，否则用内置"""
    raw = (os.getenv("NAO_BOOK_URLS") or "").strip()
    if not raw:
        return list(DEFAULT_BOOKS)
    items = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "|" in part:
            name, url = part.split("|", 1)
        else:
            name, url = "", part
        if url.startswith("http"):
            items.append((name.strip(), url.strip()))
    return items or list(DEFAULT_BOOKS)


async def pick_book(tid, fetch_book=None, rng=None, candidates=None):
    """没在追书时挑一本开始追；已经在追就返回当前那本

    返回 book dict 或 None
    """
    import random as _r
    rng = rng or _r

    data = load(tid)
    existing = current_book(data)
    if existing:
        return existing

    pool = candidates if candidates is not None else book_candidates()
    if not pool:
        return None
    name, url = rng.choice(pool)

    info = None
    if fetch_book:
        try:
            info = await fetch_book(url)
        except Exception as e:
            log_api(f"[读书] 挑书取信息失败: {e}")
            info = None

    title = (info or {}).get("title") or name or "一本小说"
    book = {
        "title": title,
        "url": url,
        "last_no": 0,
        "last_title": "",
        "intro": ((info or {}).get("intro") or "")[:200],
    }
    data.setdefault("books", []).append(book)
    save(tid, data)
    log_system(f"开始追书: 《{title}》")
    return book


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
        log_api(f"[读书] read_once 读不到书 tid={tid} books={len(data.get('books') or [])}")
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

    note_summary(data, summary)  # v16：攒着，几个点后一起说
    update_progress(data, info.get("title") or book.get("title", ""),
                    book["url"], chapter_title, info.get("intro", ""))
    mark_read(data, 1, now)
    save(tid, data)
    log_system(f"读书: {data['books'][-1]['title']} {chapter_title}（摘要 {len(summary)} 字）")
    return {"ok": True, "chapter": chapter_title, "summary": summary, "reason": "ok"}


# ===================== 指定小说（主人点名） =====================

import re as _re

BOOK_URL = _re.compile(
    r"https?://(?:www\.)?(?:fanqienovel\.com|qidian\.com)/[^\s，。、）)]+"
)
BOOK_TITLE = _re.compile(r"《([^》]{1,30})》")
FOLLOW_HINT = _re.compile(r"(去看|去读|看看|追|读一下|开始看)")


def detect_book_request(text):
    """从他的话里找「让我去看某本书」

    返回 {"url": str, "title": str} | None
    """
    text = text or ""
    m = BOOK_URL.search(text)
    if m:
        return {"url": m.group(0).rstrip(".,;!?)"), "title": ""}
    m = BOOK_TITLE.search(text)
    if m and FOLLOW_HINT.search(text):
        return {"url": "", "title": m.group(1).strip()}
    return None


async def follow(tid, url="", title="", fetch_book=None):
    """把一本书加进追更列表；已在列表里就切回那本

    返回 (book | None, 说明)
    """
    data = load(tid)
    books = data.setdefault("books", [])

    if url:
        for b in books:
            if b.get("url") == url:
                return b, "已经在追这本了"
        info = None
        if fetch_book:
            try:
                info = await fetch_book(url)
            except Exception as e:
                log_api(f"[读书] 指定书取信息失败: {e}")
                info = None
        name = (info or {}).get("title") or title or "这本小说"
        book = {"title": name, "url": url, "last_no": 0, "last_title": "",
                "intro": ((info or {}).get("intro") or "")[:200]}
        books.append(book)
        save(tid, data)
        log_system(f"主人点名追书: 《{name}》")
        return book, f"好，我去看《{name}》"

    if title:
        for b in books:
            if b.get("title") == title:
                return b, "已经在追这本了"
        return None, f"《{title}》——给我个链接吧，我找不到同名的那本"

    return None, "没听出是哪本"

# ===================== 从热榜挑书 =====================

async def pick_from_rank(tid, fetch_rank=None, fetch_book=None, rng=None, exclude=None):
    """从热榜里挑一本开始追；已在追就返回当前那本

    返回 (book | None, 说明)
    """
    import random as _r
    rng = rng or _r

    data = load(tid)
    existing = current_book(data)
    if existing:
        return existing, "已经在追这本了"

    try:
        items = await fetch_rank() if fetch_rank else []
    except Exception as e:
        log_api(f"[读书] 拉热榜失败: {e}")
        items = []
    if not items:
        return None, "热榜没拉到"

    skip = {u for _t, u in (exclude or [])}
    pool = [(t, u) for t, u in items if u not in skip]
    if not pool:
        return None, "热榜都看过了"

    title, url = rng.choice(pool)
    book, msg = await follow(tid, url=url, title=title, fetch_book=fetch_book)
    if book:
        return book, f"我在看《{book.get('title', title)}》"
    return None, msg
# ===================== 章节摘要 =====================

SUMMARY_PROMPT = (
    "把下面这段小说章节压成一两句事实：发生了什么、谁做了什么。"
    "不超过 80 字。不评价、不加引号、不写「本章」「主角」这种词，直接说人名和事。"
)
SUMMARY_SOURCE_CHARS = 3000


def _clean_summary(text, limit=SUMMARY_MAX):
    """去掉模型爱加的前后缀和多余空白"""
    s = (text or "").strip()
    s = s.strip("「」“”\"'")
    for prefix in ("摘要：", "摘要:", "概括：", "概括:"):
        if s.startswith(prefix):
            s = s[len(prefix):].strip()
    s = " ".join(s.split())
    return s[:limit]


def fallback_summary(text, limit=SUMMARY_MAX):
    """模型不可用时：取开头两句"""
    body = " ".join((text or "").split())
    if not body:
        return ""
    parts = [p for p in body.replace("！", "。").replace("？", "。").split("。") if p.strip()]
    return ("。".join(parts[:2]) + "。")[:limit]


async def summarize_chapter(text, limit=SUMMARY_MAX, call_model=None):
    """把一章正文压成一句话；模型失败就退回开头两句"""
    if not text or not text.strip():
        return ""
    snippet = text.strip()[:SUMMARY_SOURCE_CHARS]

    if call_model is None:
        try:
            from ..ai.models import call_deepseek as call_model
        except Exception:
            call_model = None

    if call_model:
        try:
            msgs = [{"role": "system", "content": SUMMARY_PROMPT},
                    {"role": "user", "content": snippet}]
            out = await call_model(msgs, max_tokens=120)
            cleaned = _clean_summary(out, limit)
            if cleaned:
                return cleaned
        except Exception as e:
            log_api(f"[读书] 摘要模型失败，用兜底: {e}")

    return fallback_summary(snippet, limit)
async def follow_request(tid, req, fetch_book=None):
    """处理「主人点名一本书」：立刻给回应，不等抓取

    返回要发出去的那句话
    """
    if not req:
        return ""
    book, msg = await follow(tid, url=req.get("url", ""), title=req.get("title", ""),
                             fetch_book=fetch_book)
    return msg
# ===================== 攒够几个点再分享（v16-E8） =====================

SHARE_AFTER = 3              # 连读 3 章的摘要攒起来
SHARE_COOLDOWN = 3 * 3600    # 两次分享至少隔 3 小时
SHARE_MAX_CHARS = 120


def note_summary(data, summary):
    """把这一章的摘要挂到待分享列表"""
    if not summary:
        return data
    pending = data.setdefault("pending", [])
    pending.append(str(summary)[:SUMMARY_MAX])
    if len(pending) > 10:
        del pending[:-10]
    return data


def share_ready(data, now=None):
    """攒够几个点了吗（且不在冷却里）"""
    pending = data.get("pending") or []
    if len(pending) < SHARE_AFTER:
        return False
    last = float(data.get("last_share_ts") or 0.0)
    return (_now(now).timestamp() - last) >= SHARE_COOLDOWN


def build_share(data):
    """把这几个点拼成一句话的素材"""
    pending = (data.get("pending") or [])[:SHARE_AFTER]
    if not pending:
        return ""
    book = current_book(data) or {}
    title = book.get("title") or ""
    body = "；".join(pending)
    text = f"《{title}》这几章：{body}" if title else f"这几章：{body}"
    return text[:SHARE_MAX_CHARS]


def mark_shared(data, now=None):
    """分享过了：清掉用掉的点，记时间"""
    pending = data.get("pending") or []
    data["pending"] = pending[SHARE_AFTER:]
    data["last_share_ts"] = _now(now).timestamp()
    return data