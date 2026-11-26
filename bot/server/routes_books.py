# ===================== 本地书阅读（v35.9.26.1） =====================
# data/books/*.txt|*.epub -> 书架 / 目录 / 正文 / 进度
# 只读本地文件；不接书源；owner-only；路径穿越和软链接逃逸拒绝。
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET

from ..infra import tenant
from .common import json_response

ROOT = Path(__file__).resolve().parents[2]
BOOKS_ROOT = ROOT / "data" / "books"
MAX_BYTES = 50 * 1024 * 1024
MAX_CHAPTERS = 2000
CACHE = {}


def _uid(request):
    return tenant.owner_id()


def _safe_book_file(raw_id):
    """id 只允许哈希/字母数字；实际文件从扫描缓存取，不接受路径。"""
    value = str(raw_id or "").strip()
    if not re.fullmatch(r"[a-f0-9]{12,32}", value):
        return None
    if not CACHE:
        _scan_books()
    return CACHE.get(value)


def _rel(path):
    return str(path.relative_to(BOOKS_ROOT)).replace("\\", "/")


def _book_id(rel, size, mtime):
    return hashlib.sha1(f"{rel}:{size}:{mtime}".encode("utf-8")).hexdigest()[:16]


def _decode_txt(raw):
    for enc in ("utf-8-sig", "utf-8", "gb18030", "big5", "latin-1"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", "replace")


class _TextExtractor(HTMLParser):
    BLOCK = {"p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "section", "article"}
    SKIP = {"script", "style", "head", "nav"}

    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        if tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        if tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def _html_text(raw):
    parser = _TextExtractor()
    try:
        parser.feed(raw)
        text = "".join(parser.parts)
    except Exception:
        text = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(text).replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in text.splitlines()]
    out = []
    blank = False
    for line in lines:
        if line:
            out.append(line)
            blank = False
        elif not blank and out:
            out.append("")
            blank = True
    return "\n".join(out).strip()


def _txt_chapters(raw):
    text = _decode_txt(raw).replace("\r\n", "\n").replace("\r", "\n")
    lines = text.splitlines()
    heading = re.compile(r"^\s*(第[零一二三四五六七八九十百千万0-9]+[章节回卷部篇]|Chapter\s+\d+|序章|楔子|尾声|后记|番外)\s*[^\n]{0,40}$", re.I)
    starts = [i for i, line in enumerate(lines) if heading.match(line)]
    chapters = []
    if len(starts) >= 2:
        for idx, start in enumerate(starts):
            end = starts[idx + 1] if idx + 1 < len(starts) else len(lines)
            body = "\n".join(lines[start:end]).strip()
            title = lines[start].strip()[:80]
            if body:
                chapters.append({"title": title or f"第 {idx + 1} 章", "content": body})
    else:
        chapters = [{"title": "正文", "content": text.strip()}] if text.strip() else []
    return chapters[:MAX_CHAPTERS]


def _epub_chapters(path):
    chapters = []
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) > 2000:
            raise ValueError("EPUB 文件数量过多")
        if "META-INF/container.xml" not in names:
            raise ValueError("EPUB 缺少 container.xml")
        root = ET.fromstring(archive.read("META-INF/container.xml"))
        ns = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}
        rootfile = root.find(".//c:rootfile", ns)
        if rootfile is None:
            raise ValueError("EPUB 缺少 OPF")
        opf_path = rootfile.attrib.get("full-path") or ""
        if opf_path not in names:
            raise ValueError("EPUB OPF 不存在")
        opf = ET.fromstring(archive.read(opf_path))
        base = os.path.dirname(opf_path)
        manifest = {}
        for item in opf.iter():
            if item.tag.endswith("}item") or item.tag == "item":
                manifest[item.attrib.get("id")] = item.attrib
        spine = []
        for item in opf.iter():
            if item.tag.endswith("}itemref") or item.tag == "itemref":
                ref = manifest.get(item.attrib.get("idref"))
                if ref and ref.get("href"):
                    spine.append(os.path.normpath(os.path.join(base, ref["href"])).replace("\\", "/"))
        # EPUB3 nav / EPUB2 ncx title mapping
        titles = {}
        for item in manifest.values():
            props = (item.get("properties") or "")
            media = item.get("media-type") or ""
            href = os.path.normpath(os.path.join(base, item.get("href") or "")).replace("\\", "/")
            if "nav" in props:
                try:
                    nav = ET.fromstring(archive.read(href))
                    for a in nav.iter():
                        if a.tag.endswith("}a") or a.tag == "a":
                            target = os.path.normpath(os.path.join(os.path.dirname(href), a.attrib.get("href", ""))).replace("\\", "/")
                            titles.setdefault(target, "".join(a.itertext()).strip())
                except Exception:
                    pass
            if media == "application/x-dtbncx+xml":
                try:
                    ncx = ET.fromstring(archive.read(href))
                    for nav in ncx.iter():
                        if nav.tag.endswith("}navPoint") or nav.tag == "navPoint":
                            label = next((x for x in nav.iter() if x.tag.endswith("}text") or x.tag == "text"), None)
                            content = next((x for x in nav.iter() if x.tag.endswith("}content") or x.tag == "content"), None)
                            if content is not None:
                                target = os.path.normpath(os.path.join(os.path.dirname(href), content.attrib.get("src", ""))).replace("\\", "/")
                                titles.setdefault(target, (label.text or "").strip() if label is not None else "")
                except Exception:
                    pass
        for href in spine[:MAX_CHAPTERS]:
            if href not in names:
                continue
            try:
                body = _html_text(archive.read(href).decode("utf-8", "replace"))
            except Exception:
                continue
            if body:
                chapters.append({"title": titles.get(href) or Path(href).stem.replace("_", " "), "content": body})
    return chapters


def _scan_books():
    CACHE.clear()
    BOOKS_ROOT.mkdir(parents=True, exist_ok=True)
    root = BOOKS_ROOT.resolve()
    for path in sorted(BOOKS_ROOT.iterdir(), key=lambda p: p.name.lower()):
        if path.name.startswith(".") or not path.is_file():
            continue
        if path.suffix.lower() not in {".txt", ".epub"}:
            continue
        try:
            resolved = path.resolve()
            if resolved != root and root not in resolved.parents:
                continue
            size = resolved.stat().st_size
            if size <= 0 or size > MAX_BYTES:
                continue
            rel = _rel(resolved)
            bid = _book_id(rel, size, int(resolved.stat().st_mtime))
            title = resolved.stem
            CACHE[bid] = {"id": bid, "title": title, "author": "", "format": resolved.suffix.lower().lstrip("."),
                          "size": size, "path": resolved, "rel": rel, "mtime": int(resolved.stat().st_mtime)}
        except Exception:
            continue
    return list(CACHE.values())


async def handle_books(request):
    books = _scan_books()
    progress = _load_progress(_uid(request))
    out = []
    for book in books:
        item = {k: book[k] for k in ("id", "title", "author", "format", "size")}
        item["progress"] = progress.get(book["id"])
        out.append(item)
    return json_response({"ok": True, "data": out, "root": "data/books", "count": len(out)})


async def handle_book(request):
    book = _safe_book_file(request.match_info.get("id"))
    if not book:
        return json_response({"ok": False, "error": "book_not_found"}, 404)
    try:
        chapters = _txt_chapters(book["path"].read_bytes()) if book["format"] == "txt" else _epub_chapters(book["path"])
    except Exception as exc:
        return json_response({"ok": False, "error": "book_parse_failed", "message": str(exc)}, 400)
    toc = [{"index": i, "title": c["title"]} for i, c in enumerate(chapters)]
    return json_response({"ok": True, "data": {**{k: book[k] for k in ("id", "title", "author", "format", "size")},
                                                "chapters": toc, "chapter_count": len(toc)},
                          "progress": _load_progress(_uid(request)).get(book["id"])})


async def handle_book_content(request):
    book = _safe_book_file(request.match_info.get("id"))
    if not book:
        return json_response({"ok": False, "error": "book_not_found"}, 404)
    try:
        chapter = max(0, int(request.query.get("chapter", 0)))
    except ValueError:
        chapter = 0
    try:
        chapters = _txt_chapters(book["path"].read_bytes()) if book["format"] == "txt" else _epub_chapters(book["path"])
    except Exception as exc:
        return json_response({"ok": False, "error": "book_parse_failed", "message": str(exc)}, 400)
    if not chapters:
        return json_response({"ok": False, "error": "empty_book"}, 400)
    chapter = min(chapter, len(chapters) - 1)
    current = chapters[chapter]
    return json_response({"ok": True, "data": {
        "book_id": book["id"], "chapter": chapter, "title": current["title"], "content": current["content"],
        "chapter_count": len(chapters), "prev": chapter - 1 if chapter > 0 else None,
        "next": chapter + 1 if chapter + 1 < len(chapters) else None,
    }})


def _load_progress(uid):
    from ..infra.conn import get_cursor
    c = get_cursor()
    try:
        c.execute("SELECT book_id,chapter,percent,updated_at FROM book_reading_progress WHERE user_id=%s", (uid,))
        return {str(r["book_id"]): {"chapter": int(r["chapter"] or 0), "percent": float(r["percent"] or 0),
                                     "updated_at": str(r["updated_at"] or "")} for r in (c.fetchall() or [])}
    finally:
        try: c.close()
        except Exception: pass


async def handle_book_progress_get(request):
    book = _safe_book_file(request.match_info.get("id"))
    if not book:
        return json_response({"ok": False, "error": "book_not_found"}, 404)
    return json_response({"ok": True, "data": _load_progress(_uid(request)).get(book["id"])})


async def handle_book_progress_put(request):
    book = _safe_book_file(request.match_info.get("id"))
    if not book:
        return json_response({"ok": False, "error": "book_not_found"}, 404)
    try:
        body = await request.json()
    except Exception:
        return json_response({"ok": False, "error": "invalid_json"}, 400)
    try:
        chapter = max(0, int(body.get("chapter", 0)))
        percent = max(0.0, min(100.0, float(body.get("percent", 0))))
    except (TypeError, ValueError):
        return json_response({"ok": False, "error": "bad_progress"}, 400)
    uid = _uid(request)
    from ..infra.conn import get_cursor
    c = get_cursor()
    try:
        if _sqlite():
            c.execute("INSERT OR REPLACE INTO book_reading_progress(user_id,book_id,chapter,percent,updated_at) "
                      "VALUES(%s,%s,%s,%s,CURRENT_TIMESTAMP)", (uid, book["id"], chapter, percent))
        else:
            c.execute("REPLACE INTO book_reading_progress(user_id,book_id,chapter,percent,updated_at) "
                      "VALUES(%s,%s,%s,%s,CURRENT_TIMESTAMP)", (uid, book["id"], chapter, percent))
        c.connection.commit()
    finally:
        try: c.close()
        except Exception: pass
    return json_response({"ok": True, "data": {"chapter": chapter, "percent": percent}})


async def handle_books_refresh(request):
    books = _scan_books()
    return json_response({"ok": True, "count": len(books), "root": "data/books"})


def _sqlite():
    try:
        from ..infra.conn import _resolve_backend
        return _resolve_backend() == "sqlite"
    except Exception:
        return False
