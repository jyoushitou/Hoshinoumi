# ===================== 小说抓取（v16-U26） =====================
# 番茄/起点都用无头浏览器取渲染后的文本：
#   - 番茄：纯 HTTP 能拿到字，但部分字被字体加密替换 → 必须走浏览器
#   - 起点：纯 HTTP 直接 202 空响应 → 必须走浏览器
#
# 设计原则：**按需启动浏览器，读完就关**；拿不到就返回 None，绝不阻塞聊天。
# 所有网络/浏览器操作都在线程里跑（Playwright 同步 API 会阻塞事件循环）。

import os
import re
from html import unescape

from ..log import log_api

FETCH_TIMEOUT = 30          # 单页超时（秒）
NAV_TIMEOUT = 20            # 页面加载超时
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# 正文容器候选（站点结构变了也不至于立刻全挂）
CONTENT_SELECTORS = (
    "div.muye-reader-content",
    "div.read-content",
    "div#content",
    "article",
    "div.chapter-content",
    "div.reader-content",
)

_TAG = re.compile(r"<[^>]+>")
_SCRIPT = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)
_SPACE = re.compile(r"[ \t\u3000]+")
_BLANK = re.compile(r"\n{3,}")
CHAPTER_LINK = re.compile(r'href="(/reader/[0-9]+)"[^>]*>([^<]{1,60})<')
BOOK_LINK = re.compile(r'href="(/page/[0-9]+)"[^>]*>([^<]{1,60})<')


def playwright_ready():
    """浏览器能不能用（装没装 + 有没有下载 chromium）"""
    try:
        import playwright  # noqa: F401
    except Exception:
        return False
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            path = p.chromium.executable_path
        return bool(path) and os.path.exists(path)
    except Exception:
        return False


def _render(url, timeout=FETCH_TIMEOUT):
    """用无头浏览器取渲染后的 HTML；失败返回 None"""
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        log_api("[小说] 没装 playwright，跳过抓取")
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            try:
                page = browser.new_page(user_agent=USER_AGENT, locale="zh-CN")
                page.set_default_timeout(NAV_TIMEOUT * 1000)
                page.goto(url, wait_until="domcontentloaded")
                # 给字体/正文一点渲染时间
                page.wait_for_timeout(1200)
                html = page.content()
                return html
            finally:
                browser.close()
    except Exception as e:
        log_api(f"[小说] 抓取失败 {url[:40]}: {e}")
        return None


async def fetch_html(url):
    """异步入口：把浏览器操作丢到线程里"""
    import asyncio
    return await asyncio.to_thread(_render, url)


# ===================== 解析 =====================

def strip_tags(html):
    """去标签、反转义、压空白"""
    if not html:
        return ""
    text = _SCRIPT.sub("", html)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</p>", "\n", text, flags=re.I)
    text = _TAG.sub("", text)
    text = unescape(text)
    text = _SPACE.sub(" ", text)
    return _BLANK.sub("\n\n", text).strip()


def parse_chapter_list(html):
    """从书籍页解析章节列表 → [(标题, url)]"""
    if not html:
        return []
    seen = set()
    chapters = []
    for path, title in CHAPTER_LINK.findall(html):
        title = strip_tags(title).strip()
        if not title or path in seen:
            continue
        seen.add(path)
        chapters.append((title, "https://fanqienovel.com" + path))
    return chapters


def parse_book(html):
    """从书籍页解析书名/作者/简介/章节"""
    if not html:
        return None
    title = ""
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    if m:
        title = strip_tags(m.group(1))[:40]
    author = ""
    m = re.search(r'作者[：:]\s*([^<\n]{1,20})', strip_tags(html))
    if m:
        author = m.group(1).strip()
    intro = ""
    m = re.search(r'作品简介\s*(.{0,300})', strip_tags(html), re.S)
    if m:
        intro = m.group(1).strip()[:200]
    return {
        "title": title,
        "author": author,
        "intro": intro,
        "chapters": parse_chapter_list(html),
    }


def parse_chapter(html):
    """从章节页解析正文；先试已知容器，再退化到最长文本块"""
    if not html:
        return ""
    for sel in CONTENT_SELECTORS:
        cls = sel.split(".")[-1]
        m = re.search(rf'<(?:div|article)[^>]*class="[^"]*{re.escape(cls)}[^"]*"[^>]*>(.*?)</(?:div|article)>',
                      html, re.S)
        if m:
            text = strip_tags(m.group(1))
            if len(text) > 100:
                return text
    # 兜底：整页去标签，取最长的一块
    text = strip_tags(html)
    blocks = [b.strip() for b in text.split("\n") if len(b.strip()) > 80]
    return max(blocks, key=len) if blocks else ""


def chapter_no(title):
    """从「第12章 xxx」里取章号"""
    m = re.search(r"第\s*(\d+)\s*[章节回]", title or "")
    return int(m.group(1)) if m else 0


async def fetch_book(url):
    html = await fetch_html(url)
    if not html:
        return None
    return parse_book(html)


async def fetch_chapter(url):
    html = await fetch_html(url)
    return parse_chapter(html) if html else ""
