# ===================== 对话历史命令（v19.2） =====================
# !history [n]：当前会话最近 n 条短期消息，默认 20，最多 100。

from .registry import command


def _limit(parts):
    for p in parts[1:]:
        if str(p).isdigit():
            return max(1, min(int(p), 100))
    return 20


def _format(rows):
    if not rows:
        return "这里还没有对话记录。"
    lines = [f"最近 {len(rows)} 条："]
    for r in rows:
        who = "她" if r.get("role") == "assistant" else "你"
        ts = str(r.get("created_at") or "")
        ts = ts[5:16] if len(ts) >= 16 else ts
        text = str(r.get("content") or "").replace("\n", " ")
        lines.append(f"{ts} {who}：{text[:120]}")
    return "\n".join(lines)


@command("history")
async def cmd_history(ctx):
    """!history [n] - 当前会话最近 n 条对话（默认 20，最多 100）"""
    from ..infra import repo_conversation

    target = str(ctx.gid) if ctx.is_group else str(ctx.uid)
    rows = repo_conversation.recent(target, limit=_limit(ctx.parts), user_id="__owner__")
    return _format(rows)
