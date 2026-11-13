# ===================== 查询类命令 =====================
# ping / uptime / log / db / usage：只读，返回文本
# 迁移自 commands.py（v5-R5）

from datetime import datetime

from ..infra.conn import get_cursor
from ..infra.repo_ai import get_recent_usage  # 数据库
from ..infra.log_sink import get_recent_logs  # 日志
from .registry import command
from ..core import clock


@command("ping")
async def cmd_ping(ctx):
    """!ping - 在线测试"""
    return "🏓 Pong！奈绪在线~"


@command("log")
async def cmd_log(ctx):
    """!log [行数] - 最近日志"""
    parts = ctx.parts
    line_count = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 20
    line_count = min(max(line_count, 1), 100)
    logs = get_recent_logs(line_count)
    return f"📋 最近{line_count}条日志：\n{logs}"


@command("db")
async def cmd_db(ctx):
    """!db - 数据库统计"""
    try:
        from ..infra.repo_query import counts

        # v17.16：命令层不再写 SQL
        n = counts(("images", "user_memory", "events", "logs", "global_keywords"))
        img_count = n["images"]
        mem_count = n["user_memory"]
        evt_count = n["events"]
        log_count = n["logs"]
        kw_count = n["global_keywords"]
        return (
            f"🗄️ 数据库状态：\n"
            f"  🖼️ 图片库: {img_count} 张\n"
            f"  🧠 对话记忆: {mem_count} 条\n"
            f"  📅 事件记忆: {evt_count} 条\n"
            f"  📋 日志: {log_count} 条\n"
            f"  🏷️ 全局关键词: {kw_count} 个"
        )
    except Exception as e:
        return f"❌ 查询数据库失败: {e}"


@command("uptime")
async def cmd_uptime(ctx):
    """!uptime - 运行时长"""
    # v18.5：启动时间来自 bot_meta / v_bot_meta（logs 有 180 天 TTL，清空不再归零）
    try:
        from ..infra import repo_meta

        info = repo_meta.uptime()
        if info:
            origin = ("v_bot_meta" if info["source"] == "view" else "bot_meta")
            return (f"⏱️ 机器人运行时长：{info['uptime_text']}\n"
                    f"  首次启动: {info['first_start']}\n"
                    f"  当前版本: {info['version'] or '未知'}\n"
                    f"  来源: {origin}（清空日志不会归零）")
    except Exception:
        pass

    try:
        from ..infra.repo_query import first_log as repo_first_log

        r = repo_first_log()
        if r and r["first_log"]:
            first_log = r["first_log"]
            # created_at 可能是 datetime 对象或字符串
            if isinstance(first_log, datetime):
                start = first_log
            else:
                start = datetime.strptime(str(first_log), "%Y-%m-%d %H:%M:%S")
            now = clock.naive()
            delta = now - start
            days = delta.days
            hours = delta.seconds // 3600
            mins = (delta.seconds % 3600) // 60
            return f"⏱️ 机器人运行时长：{days}天{hours}小时{mins}分钟\n  首次日志: {start.strftime('%Y-%m-%d %H:%M:%S')}"
        return "⏱️ 暂无运行时长数据"
    except Exception as e:
        return f"❌ 查询失败: {e}"


@command("meta")
async def cmd_meta(ctx):
    """!meta - 元数据与运行时长视图"""
    try:
        from ..infra import repo_meta

        return repo_meta.describe()
    except Exception as e:
        return f"❌ 读取元数据失败: {e}"


@command("usage")
async def cmd_usage(ctx):
    """!usage - token 用量"""
    try:
        records = get_recent_usage(10)
        if not records:
            return "📊 暂无token用量记录"
        lines = ["📊 最近10次AI调用token用量："]
        total_prompt = 0
        total_completion = 0
        total_all = 0
        for i, r in enumerate(records, 1):
            model = r["model_name"]
            pt = r["prompt_tokens"] or 0
            ct = r["completion_tokens"] or 0
            tt = r["total_tokens"] or 0
            tm = r["created_at"]
            if hasattr(tm, 'strftime'):
                tm_str = tm.strftime('%m-%d %H:%M')
            else:
                tm_str = str(tm)[5:16] if tm else ''
            lines.append(f"  {i}. [{model}] 输入{pt}+输出{ct}={tt} ({tm_str})")
            total_prompt += pt
            total_completion += ct
            total_all += tt
        lines.append(f"  ─────────────────────")
        lines.append(f"  📈 合计: 输入{total_prompt}+输出{total_completion}={total_all}")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ 查询token用量失败: {e}"

