# ===================== 命令分发入口 =====================
# v5-R5：26 个命令已全部拆到 botv/cmd/*，本文件只负责鉴权与分发
# 旧版 426 行的 if/elif 长链已删除

from botv.core import state as cfg
from .config import MASTER_QQ
from .log import log_send
from .send import send_private_msg, send_group_msg
from .cmd import registry
from .cmd import basic, query, admin, media, memory_cmd, diary_cmd, ops  # noqa: F401  导入即注册

CMD_PREFIX = "!"  # 命令前缀


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
    if not text.startswith(CMD_PREFIX):
        return False
    # 只有主人才能用命令
    if str(uid) != str(MASTER_QQ):
        return False

    cmd = text[1:].strip()
    parts = cmd.split()
    cmd_name = parts[0].lower() if parts else ""

    if registry.has(cmd_name):
        ctx = registry.CommandContext(
            parts=parts, uid=str(uid), ws=ws, is_group=is_group, gid=gid
        )
        reply = await registry.run(cmd_name, ctx)
    else:
        reply = f"❌ 未知命令: {cmd_name}\n输入 !help 查看可用命令"

    await _send_command_reply(reply, uid, ws, is_group, gid)
    return True
