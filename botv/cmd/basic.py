# ===================== 基础命令 =====================
# 纯文本类命令：只读运行时状态，返回一段文本
# 迁移自 commands.py（v5-R5 第一批），逻辑逐字未改

import botv.config as cfg  # 全局运行时变量
from ..schedule import is_workday_today  # 工作日判断
from .registry import command
from .formatters import (
    build_cmd_help, format_status_detailed, format_task_list,
    format_memory_stats, format_sticker_stats, format_clip_status,
    format_keywords, format_apikeys,
)


@command("help")
async def cmd_help(ctx):
    """!help - 显示帮助"""
    return build_cmd_help()


@command("status")
async def cmd_status(ctx):
    """!status / !status all - 运行状态"""
    parts = ctx.parts
    if "all" in parts:
        return format_status_detailed()
    lines = []
    lines.append(f"🤖 状态概览：")
    lines.append(f"  DS: {'✅' if cfg.DS_API_KEY else '❌'} | 豆包: {'✅' if cfg.DOUBAO_API_KEY else '❌'} | CLIP: {'✅' if cfg.CLIP_ENABLED else '❌'}")
    lines.append(f"  📅 {'工作日' if is_workday_today() else '休息日'} | 对话对象: {len(cfg.user_memory_pool)} | 关键词: {len(cfg.global_keyword_set)}")
    lines.append(f"  🖼️ 存档: {len(cfg.STICKER_DATA)}张 | 定时触发: {len(cfg.daily_trigger)}个")
    lines.append(f"  💬 闲聊: {len(cfg.triggered_today)}/合 | 🔧 代码模式: {'✅开启' if cfg.CODE_MODE else '关闭'}")
    lines.append(f"  使用 !status all 查看详细")
    return "\n".join(lines)


@command("task")
async def cmd_task(ctx):
    """!task - 定时任务列表"""
    return format_task_list()


@command("memory")
async def cmd_memory(ctx):
    """!memory [uid] - 对话记忆"""
    parts = ctx.parts
    if len(parts) > 1:
        target = parts[1]
        if target in cfg.user_memory_pool:
            deq = cfg.user_memory_pool[target]
            lines = [f"🧠 {target} 的对话记忆（共{len(deq)}条）："]
            for i, (u, b) in enumerate(deq[-10:], 1):
                lines.append(f"  {i}. 用户: {u[:30]}...")
                lines.append(f"     奈绪: {b[:30]}...")
            return "\n".join(lines)
        return f"🧠 {target} 暂无对话记忆"
    return format_memory_stats()


@command("sticker")
async def cmd_sticker(ctx):
    """!sticker - 表情包存档统计"""
    return format_sticker_stats()


@command("clip")
async def cmd_clip(ctx):
    """!clip - CLIP 状态"""
    return format_clip_status()


@command("keywords")
async def cmd_keywords(ctx):
    """!keywords - 全局关键词"""
    return format_keywords()


@command("apikeys")
async def cmd_apikeys(ctx):
    """!apikeys - API 密钥状态"""
    return format_apikeys()
