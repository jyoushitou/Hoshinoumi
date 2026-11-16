# ===================== 命令文本格式化 =====================
# 纯函数：把运行时状态渲染成给人看的文本
# 迁移自 commands.py（v5-R5），内容逐字未改

import time as _time
from datetime import date

from bot.core import state as cfg  # 全局运行时变量
from ..config import (
    MASTER_QQ, LISTEN_HOST, LISTEN_PORT_QQ, HEARTBEAT_INTERVAL,
    DS_MODEL, STICKER_ARCHIVE_DIR, CLIP_IMAGE_TAGS,
)
from ..schedule import is_workday_today, CHINESE_CALENDAR_OK  # 工作日判断
from ..memory import extract_keywords  # 关键词提取


_HELP_GROUPS = {
    "基础": {"help", "ping", "status", "version", "uptime", "meta", "stats",
             "usage", "log", "db", "exit", "quit", "code", "reload", "set"},
    "记忆": {"memory", "memorybook", "event", "keywords", "clear",
             "relation", "growth", "profile"},
    "媒体": {"img", "voice", "vision", "sticker", "acg", "clip", "say", "sayg"},
    "日常": {"diary", "todo", "cron", "hooks", "task", "backup", "config"},
    "阅读": {"book", "books"},
    "配置": {"persona", "apikeys", "update", "adduser", "gw", "history"},
    "插件": {"plugin"},
}


def _cmd_group(name):
    for group, names in _HELP_GROUPS.items():
        if name in names:
            return group
    return "其他"


def _cmd_desc(cmd):
    text = (getattr(cmd, "help_text", "") or "").strip()
    if text:
        return text
    doc = (getattr(cmd.handler, "__doc__", "") or "").strip()
    return doc.splitlines()[0].strip() if doc else ""


def build_cmd_help(section=None):
    """v31.3：从注册表动态生成帮助，不再维护静态命令列表。"""
    from . import registry

    section = str(section or "").strip().lower().lstrip("!")
    commands = sorted(registry.COMMANDS.values(), key=lambda c: c.name)
    if section and section not in ("all", "全部"):
        cmd = registry.COMMANDS.get(section)
        if cmd is None:
            return f"❌ 没有这个命令：{section}\n先发 !help 看列表。"
        desc = _cmd_desc(cmd)
        return (f"📋 !{cmd.name}\n{desc}\n"
                f"分类：{_cmd_group(cmd.name)}\n"
                "只给主人使用；群聊需要 @ 或命令前缀。")

    groups = {}
    for cmd in commands:
        groups.setdefault(_cmd_group(cmd.name), []).append(cmd)
    total = len(commands)
    lines = [f"📋 可用命令（{total} 个，私聊发送，仅主人有效）："]
    if section in ("all", "全部"):
        for group, cmds in groups.items():
            lines.append(f"\n【{group}】")
            for cmd in cmds:
                desc = _cmd_desc(cmd)
                lines.append(f"!{cmd.name}" + (f" - {desc}" if desc else ""))
        return "\n".join(lines)

    for group in ("基础", "记忆", "媒体", "日常", "阅读", "配置", "插件", "其他"):
        cmds = groups.get(group)
        if not cmds:
            continue
        lines.append(f"\n【{group}】")
        lines.append("  " + "  ".join(f"!{c.name}" for c in cmds))
    lines.append("\n!help <命令> 看单个说明；!help all 看完整列表。")
    return "\n".join(lines)


def format_status_detailed():
    """格式化详细状态信息：配置、API、记忆、定时任务等"""
    lines = []
    lines.append(f"🤖 主人QQ: {MASTER_QQ}")
    lines.append(f"🔌 WebSocket: {LISTEN_HOST}:{LISTEN_PORT_QQ}")
    lines.append(f"❤️ 心跳间隔: {HEARTBEAT_INTERVAL}s")
    lines.append(f"📦 消息去重缓存: {len(cfg.PROCESSED_MSG_IDS)}/80")
    lines.append("")
    lines.append(f"🧠 DeepSeek: {'✅' if cfg.DS_API_KEY else '❌'} {DS_MODEL}")
    lines.append(f"🫘 豆包: {'✅' if cfg.DOUBAO_API_KEY else '❌'}")
    lines.append(f"🖼️ CLIP: {'✅' if cfg.CLIP_ENABLED else '❌'}")
    lines.append(f"📅 chinesecalendar: {'✅ 已加载' if CHINESE_CALENDAR_OK else '⚠️ 未安装(降级weekday)'}")
    lines.append(f"🔑 搜图Token: {'✅ 已配置' if cfg.STICKER_API_ALAPI_TOKEN else '❌ 缺失'}")
    if cfg.CODE_MODE:
        elapsed = int(_time.time() - cfg.CODE_MODE_LAST_MSG_TIME) if cfg.CODE_MODE_LAST_MSG_TIME > 0 else 0
        lines.append(f"🔧 代码模式: ✅ 开启中（{elapsed//60}分{elapsed%60}秒无消息，30分钟超时）")
    else:
        lines.append(f"🔧 代码模式: ⭕ 关闭")
    lines.append("")
    lines.append(f"🗂️ 对话对象数: {len(cfg.user_memory_pool)}")
    lines.append(f"🏷️ 全局关键词数: {len(cfg.global_keyword_set)}")
    lines.append(f"🖼️ 表情包存档: {len(cfg.STICKER_DATA)} 张")
    lines.append(f"👤 本日已触发定时: {len(cfg.daily_trigger)} 个")
    lines.append(f"💬 今日闲聊次数: {len(cfg.triggered_today)}/{len(cfg.daily_chat_trigger_times) if cfg.daily_chat_trigger_times else '?'}")
    wd = "工作日" if is_workday_today() else ("周末" if date.today().weekday() >= 5 else "法定节假日")
    lines.append(f"📆 今天: {date.today().strftime('%Y-%m-%d')} {['周一','周二','周三','周四','周五','周六','周日'][date.today().weekday()]}({wd})")
    return "\n".join(lines)


def format_memory_stats():
    lines = [f"🧠 对话记忆统计："]
    lines.append(f"  总对象数: {len(cfg.user_memory_pool)}")
    for tid, deq in list(cfg.user_memory_pool.items())[:10]:
        kw = extract_keywords(deq[-1][1] if deq else "")
        lines.append(f"  [{tid}] {len(deq)}条 | 最近: {deq[-1][0][:20] if deq else '无'}...")
    if len(cfg.user_memory_pool) > 10:
        lines.append(f"  ... 还有 {len(cfg.user_memory_pool)-10} 个对象")
    return "\n".join(lines)


def format_sticker_stats():
    lines = [f"🖼️ 表情包存档统计："]
    lines.append(f"  图片总数: {len(cfg.STICKER_DATA)} 张")
    lines.append(f"  存档目录: {STICKER_ARCHIVE_DIR}/")
    uid_count = len(set().union(*[info["users"] for info in cfg.STICKER_DATA.values()])) if cfg.STICKER_DATA else 0
    lines.append(f"  贡献用户: {uid_count} 人")
    if cfg.STICKER_DATA:
        top = sorted(cfg.STICKER_DATA.keys(), key=lambda h: cfg.STICKER_DATA[h]["use_count"], reverse=True)[:3]
        lines.append(f"  热门标签: tags统计略")
    return "\n".join(lines)


def format_clip_status():
    """CLIP 自 v8 起停用，图片改由多模态模型直接看（v14-C3）"""
    if cfg.CLIP_ENABLED:
        return (f"🖼️ CLIP: ✅ 已手动启用（NAO_CLIP=1）\n"
                f"  候选标签数: {len(CLIP_IMAGE_TAGS)}\n"
                f"  注意：v8 起默认不再使用 CLIP")
    return ("🖼️ CLIP: ⏹ 已停用（v8 起改用多模态模型看图）\n"
            "  想临时启用：NAO_CLIP=1 python3 run.py")


def format_keywords():
    if not cfg.global_keyword_set:
        return "🏷️ 全局关键词: 无"
    kws = sorted(cfg.global_keyword_set)
    return f"🏷️ 全局关键词 ({len(kws)}):\n  {'、'.join(kws[:40])}"


def format_apikeys():
    return (
                f"🔑 API密钥状态：\n"
        f"  DS_API_KEY: {'✅ 已配置' if cfg.DS_API_KEY else '❌ 缺失'}\n"
        f"  DOUBAO_API_KEY: {'✅ 已配置' if cfg.DOUBAO_API_KEY else '❌ 缺失'}\n"
        f"  STICKER_API_KEY: {'✅ 已配置' if cfg.STICKER_API_ALAPI_TOKEN else '❌ 缺失'}"
    )
