# ===================== 内容类命令 =====================
# say / sayg / img / acg：会主动发消息（自带发送逻辑）
# 迁移自 commands.py（v5-R5），包含原有的「出错也不回话」行为，v6 再修

import os

from ..config import MASTER_QQ
from ..ai.client import get_character_reply
from ..image import get_best_image, fetch_and_save_acg_image
from ..send import send_private_msg, send_group_msg
from ..log import log_send
from .registry import command


def _img_msg(abs_fp):
    """构建图片消息（沿用旧命令的 file:/// 写法）"""
    return [{"type": "image", "data": {"file": f"file:///{abs_fp}"}}]


@command("say")
async def cmd_say(ctx):
    """!say <内容> - 让奈绪回一句话"""
    parts = ctx.parts
    if len(parts) < 2:
        return "用法: !say <内容>"
    content = " ".join(parts[1:])
    rep = await get_character_reply(content, str(MASTER_QQ))
    msg = [{"type": "text", "data": {"text": rep}}]
    if ctx.is_group:
        await send_group_msg(ctx.gid, msg, ctx.ws)
    else:
        await send_private_msg(ctx.uid, msg, ctx.ws)
    log_send(f"[!say] 已回复: {rep[:40]}...")
    return ""


@command("sayg")
async def cmd_sayg(ctx):
    """!sayg <群号> <内容> - 在指定群说话"""
    parts = ctx.parts
    if len(parts) < 3:
        return "用法: !sayg <群号> <内容>"
    target_gid = parts[1]
    content = " ".join(parts[2:])
    rep = await get_character_reply(content, target_gid)
    msg = [{"type": "text", "data": {"text": rep}}]
    try:
        await send_group_msg(int(target_gid), msg, ctx.ws)
        log_send(f"[!sayg] 已向群{target_gid}发送: {rep[:40]}...")
    except Exception as e:
        return f"❌ 发送失败: {e}"
    return ""


@command("img")
async def cmd_img(ctx):
    """!img <关键词...> - 手动搜图并发送"""
    parts = ctx.parts
    if len(parts) < 2:
        return "用法: !img <关键词1> <关键词2> ..."
    kws = parts[1:]
    fp = await get_best_image(kws, ctx.uid)
    if not fp:
        return f"❌ 未搜到与关键词 [{', '.join(kws)}] 相关的图片"
    abs_fp = os.path.abspath(fp)
    img_msg = _img_msg(abs_fp)
    if ctx.is_group:
        await send_group_msg(ctx.gid, img_msg, ctx.ws)
    else:
        await send_private_msg(ctx.uid, img_msg, ctx.ws)
    log_send(f"[!img] 已发送图片: {abs_fp}")
    return ""


@command("acg")
async def cmd_acg(ctx):
    """!acg - 拉一张二次元图"""
    fp = await fetch_and_save_acg_image()
    if not fp:
        return "❌ 获取ACG图片失败"
    abs_fp = os.path.abspath(fp)
    img_msg = _img_msg(abs_fp)
    if ctx.is_group:
        await send_group_msg(ctx.gid, img_msg, ctx.ws)
    else:
        await send_private_msg(ctx.uid, img_msg, ctx.ws)
    log_send(f"[!acg] 已发送ACG图: {abs_fp}")
    return ""

@command("voice")
async def cmd_voice(ctx):
    """!voice <文本> - 合成一条语音发给你"""
    from ..speech.tts import synth, available
    from ..chat.send import send_voice

    text = " ".join(ctx.args).strip()
    if not text:
        return "用法：!voice <文本>"
    if not available():
        return "没装 edge-tts。重启一次会自动尝试安装；也可以手动 pip install edge-tts"
    mp3 = await synth(text)
    if not mp3:
        return "合成失败（多半是网络或音色名不对）"
    await send_voice(ctx.uid, mp3, ctx.ws)
    return ""  # 空字符串：不再追加文本