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

VOICE_HELP = """🎙️ 声线

!voice                    看当前声线
!voice <文本>              合成一条语音发给你
!voice set <音色名>        换音色
!voice pitch <Hz>         基频偏移（-80~80）
!voice rate <百分比>       语速偏移（-50~50）
!voice vol <百分比>        音量偏移（-50~50）
!voice note <文字>         备注
!voice test [文字]         试听（不发送，只报告）
!voice reset              恢复默认"""


@command("voice")
async def cmd_voice(ctx):
    """!voice - 声线：查看 / 试听 / 调参 / 合成一条语音"""
    from ..chat.send import send_voice
    from ..speech import voice as voice_mod
    from ..speech.tts import available, synth

    args = [a for a in (ctx.args or []) if a is not None]
    sub = (args[0].lower() if args else "")

    # ---- 子命令 ----
    if sub in ("", "show", "help"):
        return VOICE_HELP if sub == "help" else voice_mod.describe()

    if sub == "reset":
        ok = voice_mod.save_profile({})
        return "✅ 已恢复默认声线" if ok else "❌ 恢复失败"

    try:
        if sub == "set":
            name = args[1].strip()
            prof = voice_mod.load_profile()
            prof["voice"] = name
            ok = voice_mod.save_profile(prof)
            return f"✅ 音色 → {name}" if ok else "❌ 保存失败"

        if sub in ("pitch", "rate", "vol"):
            field = {"pitch": "pitch_base", "rate": "rate_base",
                     "vol": "volume"}[sub]
            limit = 80 if sub == "pitch" else 50
            v = int(args[1])
            if not (-limit <= v <= limit):
                return f"❌ 要在 {-limit}~{limit} 之间"
            prof = voice_mod.load_profile()
            prof[field] = v
            ok = voice_mod.save_profile(prof)
            return f"✅ {field} → {v:+d}" if ok else "❌ 保存失败"

        if sub == "note":
            prof = voice_mod.load_profile()
            prof["notes"] = " ".join(args[1:])[:40]
            ok = voice_mod.save_profile(prof)
            return "✅ 备注已存" if ok else "❌ 保存失败"

        if sub == "test":
            text = " ".join(args[1:]) or "今天有点累，想早点睡。"
            if not available():
                return "没装 edge-tts，试听不了"
            marks = []
            for emo in voice_mod.EMOTIONS:
                p = voice_mod.emotion_params(emo)
                data = await synth(text, voice=p["voice"], rate=p["rate"],
                                   pitch=p["pitch"], volume=p["volume"])
                marks.append(f"{emo}{'✅' if data else '❌'}")
            return "🎙️ 试听：" + " ".join(marks) + "\n（没发送，只验证合成）"
    except IndexError:
        return "❌ 参数不够\n" + VOICE_HELP
    except ValueError:
        return "❌ 参数要是整数\n" + VOICE_HELP

    # ---- 默认：合成一句话发出去（带当前声线 + 情绪）----
    text = " ".join(args).strip()
    if not text:
        return VOICE_HELP
    if not available():
        return "没装 edge-tts。重启一次会自动尝试安装；也可以手动 pip install edge-tts"

    p = voice_mod.emotion_params(voice_mod.detect_emotion(ctx.uid))
    mp3 = await synth(text, voice=p["voice"], rate=p["rate"],
                      pitch=p["pitch"], volume=p["volume"])
    if not mp3:
        return "合成失败（多半是网络或音色名不对）"
    await send_voice(ctx.uid, mp3, ctx.ws)
    return ""  # 空字符串：不再追加文本