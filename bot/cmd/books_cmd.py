# ===================== 本地书命令（v24.6） =====================
from ..life import book_queue as BQ
from ..life import local_books as LB
from .registry import command


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
                         f"{r['last_chapter']}/{r['total'] or '?'}")
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
            title, chapters = LB.load_book(name)
        except Exception as e:
            return _decl(ctx) + f"加入失败：{e}"
        BQ.enqueue(ctx.uid, name, len(chapters))
        # v24.8.0：立即读第 1 章完成验证；之后空闲从第 2 章续读
        info = LB.read_chapter(name, 1)
        LB.set_progress(ctx.uid, name, info["index"])
        if BQ.get_item(ctx.uid, name):
            BQ.set_progress(ctx.uid, name, info["index"], info["total"])
        # v24.8.1：单独主动发一条自然消息，不和命令回执混在一起
        await _notify_start(ctx, title, info)
        return (_render(info) + f"\n已加入队首：《{title}》，共 {len(chapters)} 章；"
                "第 1 章已读，空闲续读。")
    if sub == "progress":
        p = LB.get_progress(ctx.uid)
        if not p:
            return _decl(ctx) + "还没有本地阅读进度。"
        return f"📖 当前：{p['name']} 第 {p['chapter']} 章"
    if sub == "next":
        p = LB.get_progress(ctx.uid)
        if not p:
            q = BQ.active(ctx.uid)
            if q:
                return _read(ctx, q["name"], int(q["last_chapter"] or 0) + 1)
            return _decl(ctx) + "还没有进度，先 !book read <文件名> 或 !book local <书名>。"
        return _read(ctx, p["name"], int(p["chapter"]) + 1)
    if sub != "read" or len(args) < 2:
        return _decl(ctx) + "用法：!book read <文件名> [章节]"
    rest = args[1:]
    chapter = 1
    if rest and rest[-1].isdigit():
        chapter = int(rest[-1])
        rest = rest[:-1]
    name = " ".join(rest).strip()
    if not name:
        return _decl(ctx) + "请给我文件名。"
    return _read(ctx, name, chapter)


async def _notify_start(ctx, title, info):
    from ..chat.send import send_short_reply
    text = (f"我开始读《{title}》了。\n"
            f"第 1 章《{info['chapter']}》：\n"
            f"{info['summary'][:180]}\n"
            f"共 {info['total']} 章，读完我再告诉你。")
    try:
        await send_short_reply(ctx.uid, text, ctx.ws, ctx.uid, False, None)
    except Exception:
        pass


def _render(info):
    return (f"📖《{info['title']}》{info['chapter']}（{info['index']}/{info['total']}）\n"
            f"摘要：{info['summary'][:300]}\n"
            "（只读本机文件，不导入数据库，不上传。）")


def _read(ctx, name, chapter):
    try:
        info = LB.read_chapter(name, chapter)
    except Exception as e:
        return _decl(ctx) + f"读不了：{e}\n只能读 data/books/ 内的 TXT/EPUB。"
    LB.set_progress(ctx.uid, name, info["index"])
    if BQ.get_item(ctx.uid, name):
        BQ.set_progress(ctx.uid, name, info["index"], info["total"])
    return _decl(ctx) + _render(info)
