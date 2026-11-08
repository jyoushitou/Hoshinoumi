# ===================== 日记展示 =====================
# 原始事件记录、最近 N 天概览
# 迁移自 diary.py（v5-R5）

from datetime import datetime, timedelta

from ..config import CST
from . import cache
from .store import get_diary_from_db, get_events_by_date, get_dialogs_by_date


def get_raw_events_text(target_id: str, date_str: str) -> str:
    """查看指定日期的原始事件记录文本（不调用 AI）"""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return "❌ 日期格式错误，请用 YYYY-MM-DD 格式，如 !diary raw 2026-07-15"

    events = get_events_by_date(target_id, date_str)
    if not events:
        return f"📭 {date_str} 没有事件记录"

    lines = [f"📅 {date_str} 的原始事件记录："]

    # 同时查对话片段
    dialogs = get_dialogs_by_date(target_id, date_str)
    if dialogs:
        lines.append("")
        lines.append("💬 对话片段：")
        for user_msg, response_text in dialogs[:10]:
            if user_msg:
                lines.append(f"  主人: {user_msg[:80]}")
            if response_text:
                lines.append(f"  奈绪: {response_text[:80]}")
        lines.append("")

    lines.append("📌 事件记忆：")
    for summary, tags in events:
        tag_str = f" [{tags}]" if tags else ""
        lines.append(f"  - {summary}{tag_str}")

    return "\n".join(lines)


async def get_diary_overview(target_id: str, days: int = 7) -> str:
    """生成最近 N 天日记概览（显示：日记已生成/有事件/空 状态）"""
    days = min(max(days, 1), 30)
    lines = [f"📖 最近 {days} 天日记概览（{target_id}）："]

    today = datetime.now(CST).date()
    for offset in range(days):
        d = (today - timedelta(days=offset)).isoformat()
        # 先查数据库
        db_text = get_diary_from_db(target_id, d)
        # 再查事件
        events = get_events_by_date(target_id, d)
        # 再查缓存
        cache_text = cache.peek(f"{target_id}_{d}")

        mark = "❌"
        if db_text or cache_text:
            mark = "✅ 日记已生成"
        elif events:
            mark = "📌 有事件（可生成）"
        else:
            mark = "⬜ 空"

        lines.append(f"  {d}  {mark}")

    return "\n".join(lines)
