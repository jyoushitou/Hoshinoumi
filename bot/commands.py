# ===================== 命令分发入口 =====================
# v5-R5：26 个命令已全部拆到 bot/cmd/*，本文件只负责鉴权与分发
# 旧版 426 行的 if/elif 长链已删除

from bot.core import state as cfg
from .config import MASTER_QQ
from .log import log_send, log_api
from .send import send_private_msg, send_group_msg
from .cmd import registry
from .cmd import (basic, query, admin, media, memory_cmd, diary_cmd, ops,
                   cron_cmd, history_cmd, gw_cmd, books_cmd, plugin_cmd, route_cmd, plan_cmd, presence_cmd)  # noqa: F401  导入即注册

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


def split_commands(text):
    """v32.4：按行拆命令；非 ! 行作为上一条的续行。"""
    lines = (text or "").splitlines()
    if not lines:
        return []
    first = lines[0].lstrip()
    if first[:1] not in ("!", "！"):
        return [text]
    commands, cur = [], []
    for line in lines:
        s = line.lstrip()
        if s[:1] in ("!", "！"):
            if cur:
                commands.append("\n".join(cur))
            cur = [line]
        elif cur:
            cur.append(line)
    if cur:
        commands.append("\n".join(cur))
    return commands


async def _handle_single_command(text, uid, ws, is_group, gid):
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
        from .cmd.channel import get_channel
        ok, reply = await get_channel().run(
            cmd_name, lambda: registry.run(cmd_name, ctx))
        if not ok and not reply:
            reply = "❌ 命令执行失败"
    else:
        log_api(f"[命令] 未知命令: {cmd_name!r} uid={uid} group={is_group} gid={gid}")
        reply = "奈绪歪头：这条我没看懂。"

    await _send_command_reply(reply, uid, ws, is_group, gid)
    return True


async def handle_command(text, uid, ws, is_group, gid):
    """处理对话命令；v32.4 支持一消息多条命令，逐条执行分别回复。"""
    text = normalize_command(text)
    if not text.startswith(CMD_PREFIX):
        return False
    commands = split_commands(text)
    if len(commands) > 1:
        for one in commands[:10]:
            await _handle_single_command(one, uid, ws, is_group, gid)
        if len(commands) > 10:
            await _send_command_reply(
                f"一次最多执行 10 条命令，已执行前 10 条（共 {len(commands)} 条）。",
                uid, ws, is_group, gid)
        return True
    return await _handle_single_command(commands[0] if commands else text,
                                        uid, ws, is_group, gid)
