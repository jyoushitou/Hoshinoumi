# ===================== 命令分发入口 =====================
# v5-R5：26 个命令已全部拆到 bot/cmd/*，本文件只负责鉴权与分发
# 旧版 426 行的 if/elif 长链已删除

from bot.core import state as cfg
from .config import MASTER_QQ
from .log import log_send, log_api
from .send import send_private_msg, send_group_msg
from .cmd import registry
from .cmd import (basic, query, admin, media, memory_cmd, diary_cmd, ops,
                   cron_cmd, history_cmd, gw_cmd, books_cmd, plugin_cmd)  # noqa: F401  导入即注册

CMD_PREFIX = "!"  # 命令前缀

# v18.20：手机输入法常打出全角符号，命令判定与参数切分前先归一化
_FULLWIDTH = str.maketrans({
    "！": "!", "：": ":", "，": ",", "；": ";", "？": "?", "（": "(", "）": ")",
})


def normalize_command(text):
    """只归一化命令文本；普通聊天原样返回，别改她的语气"""
    s = (text or "").lstrip()
    if s[:1] in ("!", "！"):
        return "!" + s[1:].translate(_FULLWIDTH)
    return text


async def _send_command_reply(reply, uid, ws, is_group, gid):
    """发送命令回复文本"""
    if not reply:
        return
    msg = [{"type": "text", "data": {"text": reply}}]
    if is_group:
        await send_group_msg(gid, msg, ws)
    else:
        await send_private_msg(uid, msg, ws)
    log_send(f"[命令回复] {reply[:50]}...")


async def handle_command(text, uid, ws, is_group, gid):
    """处理对话命令，返回True表示已处理（不再走AI回复）"""
    text = normalize_command(text)
    if not text.startswith(CMD_PREFIX):
        return False
    # v23.5.2：只有 role=owner 才能用命令；非 owner 明确拒绝
    owner = str(uid) == str(MASTER_QQ)
    if not owner:
        try:
            from .infra import repo_users, tenant
            owner = tenant.is_owner(uid) or (repo_users.get(str(uid)) or {}).get("role") == "owner"
        except Exception:
            owner = False
    if not owner:
        await _send_command_reply("这个命令只有主人能用。", uid, ws, is_group, gid)
        return True

    cmd = text[1:].strip()
    parts = cmd.split()
    cmd_name = parts[0].lower() if parts else ""

    if registry.has(cmd_name):
        ctx = registry.CommandContext(
            parts=parts, uid=str(uid), ws=ws, is_group=is_group, gid=gid
        )
        # v17.2 U4：命令走专用通道（不进调度器队列，带超时与耗时统计）
        from .cmd.channel import get_channel
        ok, reply = await get_channel().run(
            cmd_name, lambda: registry.run(cmd_name, ctx))
        if not ok and not reply:
            reply = "❌ 命令执行失败"
    else:
        # v28.7：错命令只进日志，不向用户提示命令建议
        log_api(f"[命令] 未知命令: {cmd_name!r} uid={uid} group={is_group} gid={gid}")
        reply = "奈绪歪头：这条我没看懂。"

    await _send_command_reply(reply, uid, ws, is_group, gid)
    return True

