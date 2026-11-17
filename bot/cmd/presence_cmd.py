# ===================== !doing / !presence（v34.2.2） =====================

from .registry import command


def _infer(text):
    t = text or ""
    if any(w in t for w in ("代码", "编程", "写代码", "debug")):
        return "coding"
    if any(w in t for w in ("开会", "会议", "上课")):
        return "meeting"
    if any(w in t for w in ("吃饭", "午饭", "晚饭")):
        return "eating"
    if any(w in t for w in ("看书", "读书")):
        return "reading"
    return "unknown"


@command("doing", "手动设置当前情境（!doing 写代码 / clear）")
async def cmd_doing(ctx):
    from ..life import presence
    from ..core import state as cfg

    uid = str(cfg.MASTER_QQ)
    text = " ".join(ctx.args).strip()
    if not text:
        return "用法：!doing <在做什么> / !doing clear"
    if text.lower() == "clear":
        presence.clear(uid)
        return "🧹 情境已清除"
    presence.set_presence(uid, _infer(text), text, 0, source="manual")
    return f"✅ 记下了：{text}"


@command("presence", "查看当前主账号情境")
async def cmd_presence(ctx):
    from ..life import presence
    from ..core import state as cfg

    p = presence.get_presence(str(cfg.MASTER_QQ))
    if not p:
        return "当前没有情境。"
    return f"当前：{p.get('activity')}｜{p.get('detail') or '—'}｜空闲 {p.get('idle_min', 0)} 分"
