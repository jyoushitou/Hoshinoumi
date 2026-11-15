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
        text = _decode(path.read_bytes())
        title, chapters = path.stem, _split_chapters(text)
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
