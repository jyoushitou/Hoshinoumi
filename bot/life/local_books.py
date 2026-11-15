# ===================== 本地书阅读（v24.6） =====================
# 只读 data/books/ 下的 TXT/EPUB；不导入数据库、不上传、不分发。
# 命令直读：内存进度，回复摘要 + 开头，不刷全文。

import html
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
BOOK_DIR = ROOT / "data" / "books"
MAX_CHAPTER_CHARS = 400
CHUNK_CHARS = 1000
_progress = {}   # user_id -> {"name": str, "chapter": int}
_declared = set()
_cache = {}      # path -> (mtime_ns, size, title, chapters)
_CACHE_MAX = 2

DECLARATION = (
    "本地阅读仅提供 TXT/EPUB 解析工具；文件与来源由使用者提供。\n"
    "本项目不提供、不审核、不托管任何小说内容。\n"
    "请确认你有合法阅读和使用权利。"
)

_CHAPTER_RE = re.compile(
    r"^\s*(第\s*[0-9一二三四五六七八九十百千万]+\s*[章节回]|Chapter\s+\d+)\b.*$",
    re.M | re.I)
_TAG = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"[ \t\u3000]+")


def _safe_name(name):
    raw = str(name or "").strip().replace("\\", "/")
    if not raw or raw.startswith("/") or ".." in Path(raw).parts:
        raise ValueError("只能读 data/books/ 内的文件")
    # 命令允许只写书名（不带扩展名）
    if not Path(raw).suffix:
        hits = [p for p in BOOK_DIR.glob(raw + ".*")
                if p.suffix.lower() in (".txt", ".epub")]
        if len(hits) == 1:
            raw = hits[0].name
    path = (BOOK_DIR / raw).resolve()
    base = BOOK_DIR.resolve()
    if base not in path.parents and path != base:
        raise ValueError("只能读 data/books/ 内的文件")
    if path.is_symlink():
        target = path.resolve()
        if base not in target.parents and target != base:
            raise ValueError("软链接指向 data/books/ 外")
    if path.suffix.lower() not in (".txt", ".epub"):
        raise ValueError("只支持 TXT/EPUB")
    return path


def list_books():
    BOOK_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for p in sorted(BOOK_DIR.iterdir()):
        if p.is_file() and p.suffix.lower() in (".txt", ".epub"):
            out.append({"name": p.stem, "path": p.name, "size": p.stat().st_size})
    return out


def _decode(data):
    for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _split_chapters(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return []
    matches = list(_CHAPTER_RE.finditer(text))
    if not matches:
        return [("全文", text)]
    chapters = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        title = m.group(0).strip()[:80]
        body = text[m.end():end].strip()
        chapters.append((title, body))
    return chapters


def _epub_text(path):
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        rootfile = None
        try:
            container = ET.fromstring(z.read("META-INF/container.xml"))
            for el in container.iter():
                if el.tag.endswith("rootfile"):
                    rootfile = el.attrib.get("full-path")
                    break
        except Exception:
            pass
        if not rootfile or rootfile not in names:
            rootfile = next((n for n in names if n.lower().endswith(".opf")), None)
        title = path.stem
        chapters = []
        if rootfile:
            opf = ET.fromstring(z.read(rootfile))
            base = rootfile.rsplit("/", 1)[0] if "/" in rootfile else ""
            manifest = {}
            for el in opf.iter():
                if el.tag.endswith("item"):
                    manifest[el.attrib.get("id")] = el.attrib.get("href")
                elif el.tag.endswith("title") and el.text:
                    title = el.text.strip()
            for el in opf.iter():
                if not el.tag.endswith("itemref"):
                    continue
                href = manifest.get(el.attrib.get("idref"))
                if not href:
                    continue
                full = f"{base}/{href}" if base and not href.startswith("/") else href.lstrip("/")
                if full not in names:
                    continue
                raw = z.read(full).decode("utf-8", errors="replace")
                txt = _SPACE.sub(" ", html.unescape(_TAG.sub(" ", raw)))
                txt = re.sub(r"\n{3,}", "\n\n", txt).strip()
                if len(txt) > 80:
                    chapters.append((f"第{len(chapters)+1}节", txt))
        if not chapters:
            for n in names:
                if n.lower().endswith((".xhtml", ".html", ".htm")):
                    raw = z.read(n).decode("utf-8", errors="replace")
                    txt = _SPACE.sub(" ", html.unescape(_TAG.sub(" ", raw)))
                    if len(txt) > 80:
                        chapters.append((f"第{len(chapters)+1}节", txt))
        # v24.8.6：EPUB 按 spine 顺序拼成全文，不按节切块
        if chapters:
            return title, [("全文", "".join(body for _h, body in chapters))]
        return title, chapters


def load_book(name):
    path = _safe_name(name)
    st = path.stat()
    key = str(path)
    hit = _cache.get(key)
    if hit and hit[0] == st.st_mtime_ns and hit[1] == st.st_size:
        return hit[2], hit[3]
    if path.suffix.lower() == ".epub":
        title, chapters = _epub_text(path)
    else:
        # v24.8.6：文件解码后的第一个字符就是正文第一个字
        text = _decode(path.read_bytes())
        title, chapters = path.stem, [("全文", text)]
    if len(_cache) >= _CACHE_MAX:
        _cache.pop(next(iter(_cache)))
    _cache[key] = (st.st_mtime_ns, st.st_size, title, chapters)
    return title, chapters


def read_chapter(name, chapter_no=1):
    title, chapters = load_book(name)
    if not chapters:
        raise ValueError("没有可读章节")
    idx = max(1, min(int(chapter_no), len(chapters))) - 1
    heading, body = chapters[idx]
    return {
        "title": title,
        "chapter": heading,
        "index": idx + 1,
        "total": len(chapters),
        "text": body,
        "summary": body[:MAX_CHAPTER_CHARS].strip(),
    }


def _chapter_layout(chapters):
    starts = []
    total = 0
    for _heading, body in chapters:
        starts.append(total)
        total += len(body)
    return starts, total


def chapter_start_offset(name, chapter_no=1):
    _title, chapters = load_book(name)
    if not chapters:
        return 0
    idx = max(1, min(int(chapter_no), len(chapters))) - 1
    starts, _total = _chapter_layout(chapters)
    return starts[idx]


def read_chunk(name, offset=0, limit=CHUNK_CHARS):
    """v24.8.4：按全书连续字符读，每次 1000 字，不再按章节切块。

    offset 是全书正文的全局字符位置；跨章节时直接拼下一章，
    返回起始章节/结束章节用于展示。
    """
    import bisect
    title, chapters = load_book(name)
    if not chapters:
        raise ValueError("没有可读章节")
    starts, total = _chapter_layout(chapters)
    offset = max(0, min(int(offset or 0), total))
    if offset >= total:
        return {
            "title": title, "chapter": "", "chapter_index": len(chapters),
            "end_chapter": "", "end_index": len(chapters),
            "total": len(chapters), "total_chars": total, "offset": offset,
            "chunk": "", "next_offset": total, "chars": 0, "done": True,
        }
    idx = max(0, bisect.bisect_right(starts, offset) - 1)
    # 跳过空章节
    while idx < len(chapters) and starts[idx] + len(chapters[idx][1]) <= offset:
        idx += 1
    if idx >= len(chapters):
        idx = len(chapters) - 1
    pos = offset - starts[idx]
    parts = []
    remain = max(100, int(limit))
    cur = idx
    end_idx = idx
    while cur < len(chapters) and remain > 0:
        body = chapters[cur][1]
        if pos < len(body):
            take = body[pos:pos + remain]
            if take:
                parts.append(take)
                remain -= len(take)
                end_idx = cur
            pos += len(take)
            if pos >= len(body):
                cur += 1
                pos = 0
            else:
                break
        else:
            cur += 1
            pos = 0
    chunk = "".join(parts)
    next_offset = offset + len(chunk)
    done = next_offset >= total
    first = chapters[idx][0]
    last = chapters[end_idx][0]
    label = first if end_idx == idx else f"{first} → {last}"
    return {
        "title": title,
        "chapter": label,
        "chapter_index": idx + 1,
        "end_chapter": last,
        "end_index": end_idx + 1,
        "total": len(chapters),
        "total_chars": total,
        "offset": offset,
        "next_offset": next_offset,
        "chunk": chunk,
        "chars": len(chunk),
        "done": done,
    }


def set_progress(user_id, name, chapter):
    _progress[str(user_id)] = {"name": str(name), "chapter": int(chapter)}


def get_progress(user_id):
    return _progress.get(str(user_id))


def declaration_once(user_id):
    uid = str(user_id)
    if uid in _declared:
        return ""
    _declared.add(uid)
    return DECLARATION + "\n"
