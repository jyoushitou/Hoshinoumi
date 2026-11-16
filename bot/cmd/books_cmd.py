# ===================== 本地书命令（v24.6） =====================
import asyncio

from ..life import book_memory
from ..life import book_queue as BQ
from ..life import local_books as LB
from .registry import command

_bg_tasks = set()


def _spawn(coro):
    task = asyncio.create_task(coro)
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)
    return task


def _decl(ctx):
    return LB.declaration_once(ctx.uid)


@command("books")
async def cmd_books(ctx):
    """!books - 列出 data/books/ 本地书"""
    if ctx.is_group:
        return ""
    try:
        rows = LB.list_books()
    except Exception as e:
        return f"本地书目录读取失败：{e}"
    lines = [_decl(ctx) + "📚 data/books/ 本地书"]
    if not rows:
        lines.append("  （空）把 TXT/EPUB 放进 data/books/，文件名即书名。")
    else:
        for r in rows:
            lines.append(f"  {r['name']}（{r['size'] // 1024} KB）")
    return "\n".join(lines)


@command("book")
async def cmd_book(ctx):
    """!book read <文件名> [章节] / next / progress"""
    if ctx.is_group:
        return ""
    args = list(ctx.args)
    if not args:
        return _decl(ctx) + "用法：!book read <文件名> [章节]｜!book next｜!book progress"
    sub = args[0].lower()
    if sub == "queue":
        rows = BQ.list_queue(ctx.uid)
        if not rows:
            return _decl(ctx) + "本地阅读队列为空。用 !book local <书名> 加入。"
        lines = [_decl(ctx) + "📚 本地阅读队列"]
        for r in rows:
            lines.append(f"  {r['status']}  {r['name']}  "
                         f"已读 {r.get('char_offset', 0)} 字（全书连续）")
        return "\n".join(lines)
    if sub == "remove":
        if len(args) < 2:
            return _decl(ctx) + "用法：!book remove <书名>"
        name = " ".join(args[1:]).strip()
        ok = BQ.remove(ctx.uid, name)
        return _decl(ctx) + ("已移出队列。" if ok else "队列里没有这本。")
    if sub == "local":
        if len(args) < 2:
            return _decl(ctx) + "用法：!book local <书名>"
        name = " ".join(args[1:]).strip()
        try:
            # 只做路径/后缀校验，不解析 14MB 全文，避免命令 15 秒超时
            LB._safe_name(name)
        except Exception as e:
            return _decl(ctx) + f"加入失败：{e}"
        BQ.enqueue(ctx.uid, name, 0)
        _spawn(_read_first_and_notify(ctx, name))
        return _decl(ctx) + (f"已加入队首：《{name}》。\n"
                              "正在解析全书首个 1000 字；摘要只入库，不主动发。"
                              "空闲从下一段 1000 字续读。")
    if sub == "progress":
        p = LB.get_progress(ctx.uid)
        if not p:
            return _decl(ctx) + "还没有本地阅读进度。"
        q = BQ.get_item(ctx.uid, p["name"])
        if q:
            return f"📖 当前：{p['name']}，已读 {q.get('char_offset', 0)} 字"
        return f"📖 当前：{p['name']}"
    if sub == "next":
        q = BQ.active(ctx.uid)
        if q:
            return await _read_chunk(ctx, q["name"], int(q.get("char_offset") or 0))
        p = LB.get_progress(ctx.uid)
        if not p:
            return _decl(ctx) + "还没有进度，先 !book read <文件名> 或 !book local <书名>。"
        BQ.repair_done(ctx.uid, p["name"])
        q = BQ.active(ctx.uid)
        if q and q["name"] == p["name"]:
            return await _read_chunk(ctx, q["name"], int(q.get("char_offset") or 0))
        return await _read_chunk(ctx, p["name"], 0)
    if sub != "read" or len(args) < 2:
        return _decl(ctx) + "用法：!book read <文件名>"
    name = " ".join(args[1:]).strip()
    if not name:
        return _decl(ctx) + "请给我文件名。"
    # v24.8.6：从文件第一个字开始，不按章节定位
    return await _read_chunk(ctx, name, 0)


async def _read_first_and_notify(ctx, name):
    """后台解析并读全书首个 1000 字，避免 15s 命令超时。"""
    try:
        title, chapters = LB.load_book(name)
        BQ.set_total(ctx.uid, name, len(chapters))
        info = LB.read_chunk(name, 0)
        LB.set_progress(ctx.uid, name, info["end_index"])
        BQ.set_progress(ctx.uid, name, info["end_index"], info["total"],
                        status=("done" if info["done"] else "reading"),
                        offset=info["next_offset"])
        summary = await _chunk_summary(info)
        if "摘要生成失败" not in summary:
            try:
                book_memory.remember_chunk(ctx.uid, ctx.uid, title, info, summary)
                if info["done"]:
                    book_memory.remember_finished(ctx.uid, ctx.uid, title, info["total_chars"])
            except Exception:
                pass
        # v29.4：自动首读只入库，不主动发摘要/错误；手动 !book next 才回
    except Exception as e:
        try:
            BQ.mark_error(ctx.uid, name)
        except Exception:
            pass
        try:
            from ..log import log_err
            log_err(f"[本地阅读] 首段读取失败 {name}: {e}")
        except Exception:
            pass


async def _chunk_summary(info):
    """把这一块交给模型总结；不返回正文。"""
    try:
        from ..life import reading
        text = await reading.summarize_chapter(info["chunk"][:3000], allow_text_fallback=False)
        return (text or "").strip()[:500] or "（这段摘要生成失败，进度已记录）"
    except Exception:
        return "（这段摘要生成失败，进度已记录）"


async def _read_chunk(ctx, name, offset=0):
    try:
        info = LB.read_chunk(name, offset)
    except Exception as e:
        return _decl(ctx) + f"读不了：{e}\n只能读 data/books/ 内的 TXT/EPUB。"
    LB.set_progress(ctx.uid, name, info["end_index"])
    q = BQ.get_item(ctx.uid, name)
    if q:
        BQ.set_progress(ctx.uid, name, info["end_index"], info["total"],
                        status=("done" if info["done"] else "reading"),
                        offset=info["next_offset"])
    summary = await _chunk_summary(info)
    if "摘要生成失败" not in summary:
        try:
            book_memory.remember_chunk(ctx.uid, ctx.uid, info["title"], info, summary)
            if info["done"]:
                book_memory.remember_finished(ctx.uid, ctx.uid, info["title"], info["total_chars"])
        except Exception:
            pass
    return (_decl(ctx)
            + f"📖《{info['title']}》"
            f"（第 {info['offset'] + 1} 字到第 {info['offset'] + info['chars']} 字）\n"
            + f"摘要：{summary}\n"
            + "（每次 1000 字，只读本机文件，不上传。）")
