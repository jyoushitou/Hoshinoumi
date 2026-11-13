# ===================== 日记命令 =====================
# diary：查看 / 生成 / 概览 / 原始事件
# 迁移自 commands.py（v5-R5）

from datetime import datetime, date

from ..config import MASTER_QQ
from ..diary import generate_diary, get_diary_overview, get_raw_events_text
from .registry import command


@command("diary")
async def cmd_diary(ctx):
    """!diary [日期|list|raw ...] - 日记"""
    parts = ctx.parts
    target = str(MASTER_QQ)  # 默认为主人生成日记（events表存的主人ID）
    if len(parts) > 1:
        sub = parts[1].lower()
        if sub == "list":
            # !diary list [天数] - 最近几天日记概览
            days = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 7
            days = min(max(days, 1), 30)
            return await get_diary_overview(target, days)
        elif sub == "raw":
            # !diary raw <日期> - 查看原始事件记录
            if len(parts) > 2:
                try:
                    datetime.strptime(parts[2], "%Y-%m-%d")
                    return get_raw_events_text(target, parts[2])
                except ValueError:
                    return "❌ 日期格式错误，请用 YYYY-MM-DD 格式，如 !diary raw 2026-07-15"
            return "用法: !diary raw <YYYY-MM-DD>"
        else:
            # !diary <日期> / !diary force <日期>
            force_regen = False
            date_arg = parts[1]
            if date_arg.lower() == "force" and len(parts) > 2:
                force_regen = True
                date_arg = parts[2]
            try:
                datetime.strptime(date_arg, "%Y-%m-%d")
                d = date_arg
                diary_text = await generate_diary(target, d, force=force_regen)
                prefix = f"📖 {d} 的日记（已重新生成）：\n" if force_regen else f"📖 {d} 的日记：\n"
                return prefix + diary_text
            except ValueError:
                return (
                    "❌ 无法识别的参数。用法：\n"
                    "  !diary                  - 今天的日记\n"
                    "  !diary <YYYY-MM-DD>     - 指定日期的日记\n"
                    "  !diary force <YYYY-MM-DD> - 强制重新生成指定日期日记\n"
                    "  !diary list [天数]       - 最近几天概览\n"
                    "  !diary raw <YYYY-MM-DD> - 原始事件记录"
                )
    # !diary - 今天的日记
    d = date.today().isoformat()
    diary_text = await generate_diary(target, d)
    return f"📖 {d} 的日记：\n{diary_text}"
