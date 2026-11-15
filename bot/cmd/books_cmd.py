# ===================== 本地书命令（v24.6） =====================
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
    if sub == "progress":
        p = LB.get_progress(ctx.uid)
        if not p:
            return _decl(ctx) + "还没有本地阅读进度。"
        return f"📖 当前：{p['name']} 第 {p['chapter']} 章"
    if sub == "next":
        p = LB.get_progress(ctx.uid)
        if not p:
            return _decl(ctx) + "还没有进度，先 !book read <文件名>。"
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


def _read(ctx, name, chapter):
    try:
        info = LB.read_chapter(name, chapter)
    except Exception as e:
        return _decl(ctx) + f"读不了：{e}\n只能读 data/books/ 内的 TXT/EPUB。"
    LB.set_progress(ctx.uid, name, info["index"])
    return (
        _decl(ctx)
        + f"📖《{info['title']}》{info['chapter']}（{info['index']}/{info['total']}）\n"
        + f"摘要：{info['summary'][:300]}\n"
        + "（只读本机文件，不导入数据库，不上传。）"
    )
