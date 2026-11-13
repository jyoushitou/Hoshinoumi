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


def build_cmd_help():
    """构建帮助文本：列出所有可用命令及说明"""
    return (
        "📋 可用命令（私聊发送，仅主人有效）：\n"
        "!help          - 显示本帮助\n"
        "!status        - 查看运行状态概览\n"
        "!status all    - 查看所有详细参数\n"
        "!task          - 查看定时任务列表与下次触发时间\n"
        "!memory        - 查看对话记忆统计\n"
        "!memory <uid>  - 查看指定对象的记忆详情\n"
        "!sticker       - 查看表情包存档统计\n"
        "!clip          - 查看CLIP状态\n"
        "!keywords      - 查看全局关键词\n"
        "!apikeys       - 查看API密钥状态（隐藏完整值）\n"
        "!reload        - 重新加载API密钥和记忆\n"
        "!set <键> <值>  - 修改配置（仅支持部分参数）\n"
        "                支持: master_qq, heartbeat\n"
        "!say <内容>     - 让奈绪主动说一句话\n"
        "!sayg <群号> <内容> - 让奈绪在指定群说话\n"
        "!img <关键词>   - 手动搜图并发送\n"
        "!acg           - 获取一张ACG二次元图\n"
        "!profile [uid] - 查看对象画像；!profile set <uid> <字段> <值> 写入\n"
        "!todo [文字]   - 查看日程；!todo 周五下午三点 面试 添加\n"
        "!voice <文本>  - 合成一条语音（需要 edge-tts）\n"
        "!memorybook    - 记忆本：认识多久、关系、口头禅\n"
        "!growth        - 成长轨迹：认识天数、关系进度、一起经历过多少事\n"
        "!persona [名字] - 查看/切换角色卡（personas/ 下的目录）\n"
        "!stats         - 今日统计：回复/配图/语音/群聊接话率\n"
        "!config [k] [v]- 查看/修改运行时参数\n"
        "!version       - 当前版本、提交、运行时长\n"
        "!cron          - 定时消息（add/once/every/del/on/off）\n"
        "!event <uid>   - 查看指定对象的事件记忆\n"
        "!clear <uid>   - 清除指定对象的对话记忆\n"
        "!log <行数>     - 查看最近日志（默认20行）\n"
        "!db            - 查看数据库连接状态\n"
        "!usage         - 查看最近10次token用量和使用模型\n"
        "!uptime        - 查看机器人运行时长\n"
        "!meta          - 查看机器人元数据（首次启动/版本/运行时长视图）\n"
        "!ping          - 测试机器人是否在线\n"
        "!code          - 开启代码模式（知识正确性优先于人设，30分钟无消息自动退出）\n"
        "!code off      - 手动退出代码模式\n"
        "!diary          - 查看今天的日记（AI生成）\n"
        "!diary <日期>   - 查看指定日期日记，如 !diary 2026-07-15\n"
        "!diary list [天数] - 最近几天日记概览（默认7天）\n"
        "!diary raw <日期>  - 查看指定日期的原始事件记录\n"
        "!exit / !quit    - 安全退出程序（停止所有服务）\n"
        )


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
