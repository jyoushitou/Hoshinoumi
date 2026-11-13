# ===================== 消息发送 =====================
# 选图 + WebSocket 投递（v5-R4）
# 迁移自 bot/send.py：这里只负责「发」，组装在 chat/reply.py

import asyncio
import time
import json
import os
import random

from ..config import STICKER_FACE_IDS, STICKER_ARCHIVE_DIR
from bot.core import state as cfg
from ..log import log_send, log_err, log_api, log_system
from ..image import search_local_image_by_tags, get_best_image
from ..memory import extract_keywords
from ..utils import encode_image_base64, make_image_msg
from ..infra.conn import get_cursor
from ..speech.tts import synth as tts_synth  # v11-A10：语音合成
from .reply import build_reply_message
from .cache import remember as remember_message

# ===== 语音（v11-A10）=====
VOICE_PROB = 0.08        # 每条回复变成语音的概率
VOICE_COOLDOWN = 1200    # 同一个人 20 分钟内最多一条语音
VOICE_MIN_LEN = 4        # 太短（「嗯」）不合成
VOICE_MAX_LEN = 60       # 太长不合成
_last_voice_ts = {}      # {target: ts}


def make_record_msg(mp3):
    """NapCat 的语音消息段（base64 直传，不用落地文件）"""
    import base64
    return [{"type": "record", "data": {"file": "base64://" + base64.b64encode(mp3).decode()}}]


async def send_voice(target, mp3, ws, is_group=False):
    """发一条语音"""
    msg = make_record_msg(mp3)
    if is_group:
        await send_group_msg(target, msg, ws)
    else:
        await send_private_msg(target, msg, ws)


def _voice_worthy(text):
    """剥掉标点和空白后还够长才值得念（v16 修复：别发 1 秒的「……」）"""
    import re as _re
    core = _re.sub(r"[\s\W_]+", "", text or "", flags=_re.UNICODE)
    return len(core) >= VOICE_MIN_LEN


async def maybe_send_voice(text, target, ws, is_group=False):
    """按概率/冷却决定要不要把这句话念出来。返回是否发了"""
    import time as _t
    if is_group:
        return False  # 群里先不发语音，太吵
    if not (VOICE_MIN_LEN <= len(text or "") <= VOICE_MAX_LEN):
        return False
    if not _voice_worthy(text):          # v17.13：「……」「？？？」不合成
        return False
    from ..core import tunables
    if random.random() > tunables.get("voice_prob", VOICE_PROB):
        return False
    now = _t.time()
    if now - _last_voice_ts.get(target, 0.0) < VOICE_COOLDOWN:
        return False
    # v17.12：按当前情绪 + 角色声线合成
    try:
        from ..speech import voice as voice_mod
        _p = voice_mod.emotion_params(voice_mod.detect_emotion(target))
        mp3 = await tts_synth(text, voice=_p["voice"], rate=_p["rate"],
                              pitch=_p["pitch"], volume=_p["volume"])
    except Exception:
        mp3 = await tts_synth(text)
    if not mp3:
        return False
    await send_voice(target, mp3, ws)
    _last_voice_ts[target] = now
    try:
        from ..core import metrics
        metrics.inc("voices")
    except Exception:
        pass
    return True


def select_best_sticker(uid, ctx=""):
    """旧接口兼容：优先查新库→其次旧存档→最后QQ表情兜底"""
    kws = extract_keywords(ctx)  # 从上下文提取关键词
    log_api(f"[选图] uid={uid}, ctx_kws={kws}")  # 日志记录
    # 新库查
    results = search_local_image_by_tags(kws, limit=3)  # 按标签搜索新库（最多3张）
    if results:  # 新库命中
        log_api(f"[选图] 新库命中: {results[0][2]}")  # 日志记录
        try:
            c = get_cursor()  # 获取数据库游标
            c.execute("UPDATE images SET use_count=use_count+1 WHERE md5_hash=%s", (results[0][0],))  # 使用次数+1
            c.connection.commit()  # 提交事务
        except:
            pass  # 更新失败不影响
        return results[0][2]  # 返回文件路径
    # v17.13：没提取到关键词就退 QQ 表情，别拿存档图乱甩
    if not kws:
        face_id = str(random.choice(STICKER_FACE_IDS))
        log_api(f"[选图] 无关键词，退 QQ 表情: {face_id}")
        return face_id

    # 旧存档查
    uid_s = str(uid)  # 用户ID转字符串
    if uid_s in cfg.USER_STICKER_ARCHIVE and cfg.USER_STICKER_ARCHIVE[uid_s]:  # 用户有旧存档
        for h in reversed(cfg.USER_STICKER_ARCHIVE[uid_s]):  # 从最新到最旧遍历
            if h in cfg.STICKER_DATA:  # 表情包数据存在
                fp = os.path.join(STICKER_ARCHIVE_DIR, f"{h}.jpg")  # 旧存档文件路径
                if os.path.exists(fp):  # 文件存在
                    log_api(f"[选图] 旧存档命中: {fp}")  # 日志记录
                    return fp  # 返回文件路径
    # 兜底QQ表情
    face_id = str(random.choice(STICKER_FACE_IDS))  # 随机选一个QQ表情ID
    log_api(f"[选图] 兜底QQ表情: {face_id}")  # 日志记录
    return face_id  # 返回表情ID


async def _delayed_jieba_fallback(dialog, action, uid):
    """延迟1分钟后用jieba提取关键词搜图兜底（后台任务）
    注意：此函数已不再被build_reply_message调用，保留以兼容旧代码"""
    await asyncio.sleep(60)  # 等待60秒
    search_kws = extract_keywords(f"{dialog} {action}")  # 用jieba从对话+动作中提取关键词
    log_api(f"[构建回复] jieba兜底关键词(延迟1min): {search_kws}")  # 日志记录
    if search_kws:  # 提取到关键词
        fp = await get_best_image(search_kws, uid)  # 按关键词搜图
        if fp:  # 搜到图片
            abs_fp = os.path.abspath(fp)  # 转为绝对路径（NapCat需要绝对路径）
            log_api(f"[构建回复] jieba兜底搜到图片(延迟1min): {abs_fp}")  # 日志记录
            img_msg = [{"type":"image","data":{"file":abs_fp}}]  # 构建图片消息
            ws = cfg.active_ws_qq  # 获取当前WebSocket连接
            if ws and not getattr(ws, "closed", False):  # 连接有效
                try:
                    await send_private_msg(uid, img_msg, ws)  # 发送图片
                    log_api(f"[构建回复] 延迟兜底图片已发送给{uid}")
                except Exception as e:
                    log_err(f"[构建回复] 延迟兜底发送失败: {e}")  # 日志记录
        else:  # 搜图无结果
            log_api(f"[构建回复] jieba兜底搜图无结果(延迟1min)")


def _alive(ws):
    """连接是否可用"""
    return bool(ws) and not getattr(ws, "closed", False)


def _enqueue(payload, label):
    """连接不可用时把消息放进待补发队列（v5-F6）"""
    cfg.pending_outbox.append(payload)
    log_err(f"{label}: 连接不可用，消息已入队（队列 {len(cfg.pending_outbox)} 条）")


def _kind_of_label(label):
    """把中文标签归到出站统计的 kind（v17.2）"""
    text = str(label)
    if "撤回" in text or "get_msg" in text or "取消息" in text:
        return "query"
    if "戳" in text:
        return "poke"
    if "图" in text:
        return "image"
    if "语音" in text or "voice" in text:
        return "voice"
    if "群" in text:
        return "group"
    return "chat"

async def _send_or_queue(action, params, ws, label, want_response=False, timeout=8):
    """发送一条消息；连接断了就入队，等重连补发

    want_response=True 时会给消息带一个 echo，并等 NapCat 回包，
    拿到 data（里面有 message_id），用于「撤回」这类需要 id 的操作（v12-A13）。
    """
    echo = None
    fut = None
    if want_response:
        import uuid
        echo = uuid.uuid4().hex
        payload_obj = {"action": action, "params": params, "echo": echo}
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        cfg.pending_echo[echo] = fut
        payload = json.dumps(payload_obj, ensure_ascii=False)
    else:
        payload = json.dumps({"action": action, "params": params}, ensure_ascii=False)

    # v17.2：统一交给出站口（锁 / 入队 / echo 都在里面）
    from ..egress.outbound import get_outbound
    out = get_outbound()
    out.bind(ws)
    if want_response:
        return await out.send(action, params, label=label,
                              kind=_kind_of_label(label), want_response=True,
                              timeout=timeout)
    ok = await out.send(action, params, label=label, kind=_kind_of_label(label))
    return bool(ok)

    if fut is None:
        return True

    try:
        resp = await asyncio.wait_for(fut, timeout)
        return resp
    except Exception:
        return None
    finally:
        cfg.pending_echo.pop(echo, None)


async def request_action(action, params, ws, label="请求", timeout=8):
    """发一个请求并等回包（get_msg / 撤回 / 回戳都走它，v12）"""
    return await _send_or_queue(action, params, ws, label, want_response=True, timeout=timeout)


async def flush_outbox(ws):
    """重连后补发断线期间积压的消息，返回补发条数（v17.2 走出站口）"""
    from ..egress.outbound import get_outbound
    out = get_outbound()
    out.bind(ws)
    return await out.flush()


async def send_private_msg(qq, msg, ws, want_response=False):
    """通过WebSocket发送私聊消息（断线自动入队）"""
    return await _send_or_queue("send_private_msg", {"user_id": qq, "message": msg},
                                ws, "私聊", want_response=want_response)


async def send_group_msg(gid, msg, ws, want_response=False):
    """通过WebSocket发送群聊消息（断线自动入队）"""
    return await _send_or_queue("send_group_msg", {"group_id": gid, "message": msg},
                                ws, "群聊", want_response=want_response)


# 气泡之间的间隔（秒）：随机，避免机械节奏（v6-A12）
BUBBLE_DELAY_RANGE = (1.5, 3.0)


def bubble_delay():
    """返回下一条气泡前的等待秒数"""
    return random.uniform(*BUBBLE_DELAY_RANGE)


def _remember_outgoing(resp, msg):
    """v18.6：把刚发出的文本记进缓存（拿到 message_id 才记）"""
    try:
        data = (resp or {}).get("data") or {}
        mid = data.get("message_id") or data.get("message_id_str")
        if not mid:
            return
        if isinstance(msg, list):
            txt = "".join(str((s.get("data") or {}).get("text", ""))
                          for s in msg if s.get("type") == "text").strip()
        else:
            txt = str(msg or "").strip()
        if txt:
            remember_message(mid, "友利奈绪", txt)
    except Exception:
        pass


async def send_short_reply(tid, text, ws, uid, is_group=False, kws=None):
    """发送完整回复：构建消息→逐条发送（文本+图片）"""
    if is_duplicate_reply(tid, text):  # v16.0.5：同一句话短时间内不重复发
        log_api("[发送] 与上一条重复，跳过")
        try:
            from ..core import metrics
            metrics.inc("duplicate_reply")
        except Exception:
            pass
        return False
    parts = await build_reply_message(text, uid, kws, is_group)  # 构建回复消息列表（带发图择时）
    log_api(f"[发送] 共{len(parts)}条消息: {[p[0] for p in parts]}")  # 日志记录消息数量
    # v18.6：只有真实连接 + 异步接收时才等回包拿 message_id；测试/回退模式不等
    capture = (ws is not None and ws is cfg.active_ws_qq
               and os.getenv("NAO_ASYNC_DISPATCH", "1") not in ("0", "false", "False"))
    for ptype, msg in parts:  # 遍历每条消息
        log_api(f"[发送] 类型={ptype}, 内容预览={str(msg)[:60]}")  # 日志记录
        want = capture and ptype == "text"
        if is_group:  # 群聊
            resp = await send_group_msg(tid, msg, ws, want_response=want)  # 发送群消息
        else:  # 私聊
            resp = await send_private_msg(tid, msg, ws, want_response=want)  # 发送私聊消息
        if want:
            _remember_outgoing(resp, msg)
        if ptype == "text":
            try:  # v19.1：出站写短期对话流；失败不阻塞发送
                from ..infra import repo_conversation
                _txt = ""
                if isinstance(msg, list):
                    _txt = "".join(str((x.get("data") or {}).get("text", ""))
                                   for x in msg if isinstance(x, dict) and x.get("type") == "text")
                else:
                    _txt = str(msg or "")
                _mid = None
                if isinstance(resp, dict):
                    _mid = (resp.get("data") or {}).get("message_id")
                repo_conversation.append(
                    target_id=str(tid), content=_txt, role="assistant", channel="qq",
                    thread_id=f"qq:{'group' if is_group else 'private'}:{tid}",
                    message_id=_mid,
                )
            except Exception as _e:
                log_api(f"[对话] 出站写入失败（忽略）: {_e}")
        await asyncio.sleep(bubble_delay())  # 每条间隔随机 1.5~3 秒，像真人打字
    log_send(f"回复:{text[:40]}")  # 日志记录发送


async def send_segmented_reply(tid, text, ws, uid, is_group=False, kws=None):
    """v19.3：按【语音】/[文字] 分段发送；无标记时等同 send_short_reply"""
    from .segments import parse, strip_markers, to_text
    from ..core import state as _cfg

    if is_group or _cfg.CODE_MODE:
        return await send_short_reply(tid, to_text(text), ws, uid, is_group, kws)

    segs = parse(text)
    if not any(kind == "voice" for kind, _body in segs):
        return await send_short_reply(tid, strip_markers(text), ws, uid, is_group, kws)

    sent_any = False
    first_text = True
    for kind, body in segs:
        if kind == "text":
            await send_short_reply(tid, body, ws, uid, is_group,
                                   kws if first_text else None)
            first_text = False
            sent_any = True
            continue
        # 语音段：过长/合成失败都降级文字
        if len(body) > 120:
            await send_short_reply(tid, body, ws, uid, is_group,
                                   kws if first_text else None)
            first_text = False
            sent_any = True
            continue
        try:
            from ..speech.voice import detect_emotion, emotion_params
            from ..speech.tts import synth as tts_synth
            params = emotion_params(detect_emotion())
            params.pop("emotion", None)
            mp3 = await tts_synth(body, **params)
        except Exception as e:
            log_api(f"[语音] 分段合成失败，降级文字: {e}")
            mp3 = None
        if not mp3:
            await send_short_reply(tid, body, ws, uid, is_group,
                                   kws if first_text else None)
            first_text = False
            sent_any = True
            continue
        await send_voice(tid, mp3, ws, is_group)
        sent_any = True
    return sent_any


async def send_sticker_private(qq, ws, uid, ctx=""):
    """发送私聊表情包"""
    s = select_best_sticker(uid, ctx)  # 选择最佳表情包（带上下文，避免甩无关图）
    if isinstance(s, str):  # 返回的是QQ表情ID（字符串）
        await send_private_msg(qq, [{"type":"face","data":{"id":s}}], ws)  # 发送QQ表情
    else:  # 返回的是文件路径
        img_msg = make_image_msg(s)  # 构建图片消息
        if img_msg:  # 构建成功
            await send_private_msg(qq, img_msg, ws)  # 发送图片


async def send_sticker_group(gid, ws, uid, ctx=""):
    """发送群聊表情包"""
    s = select_best_sticker(uid)  # 选择最佳表情包
    if isinstance(s, str):  # 返回的是QQ表情ID（字符串）
        await send_group_msg(gid, [{"type":"face","data":{"id":s}}], ws)  # 发送QQ表情
    else:  # 返回的是文件路径
        img_msg = make_image_msg(s)  # 构建图片消息
        if img_msg:  # 构建成功
            await send_group_msg(gid, img_msg, ws)  # 发送图片


# ===================== 打错字再撤回（v12-A13） =====================
# 真人才会这样：发出去发现错了 → 撤回 → 重发对的。低频，一周最多两次。

TYPO_PROB = 0.03
TYPO_WEEK_LIMIT = 2
TYPO_MIN_LEN, TYPO_MAX_LEN = 4, 30
TYPO_WEEK_SECONDS = 7 * 86400


def make_typo(text):
    """造一个「手滑」的版本：交换两个相邻字符"""
    chars = list(text or "")
    if len(chars) < TYPO_MIN_LEN:
        return text
    for i in range(len(chars) - 1, 0, -1):
        if chars[i] != chars[i - 1]:
            chars[i], chars[i - 1] = chars[i - 1], chars[i]
            return "".join(chars)
    return "".join(chars[1:]) or text


def _typo_quota_ok(now):
    recent = [t for t in cfg.typo_history if now - t < TYPO_WEEK_SECONDS]
    cfg.typo_history[:] = recent
    return len(recent) < TYPO_WEEK_LIMIT


async def try_typo_recall(target, text, ws):
    """有概率先发一条打错的、撤回，再发正确的。返回是否真的演了一次

    v17.9：如果这句话已经用语音念出来了，就不再演撤回——
    语音收不回来，撤回文字只会造成「说的和写的不一致」。
    """
    if _last_voice_ts.get(target) and (time.time() - _last_voice_ts[target]) < 120:
        log_api("[撤回] 这句刚发过语音，跳过撤回")
        return False
    if random.random() > TYPO_PROB:
        return False
    if not (TYPO_MIN_LEN <= len(text or "") <= TYPO_MAX_LEN):
        return False
    import time as _t
    now = _t.time()
    if not _typo_quota_ok(now):
        return False

    typo = make_typo(text)
    if typo == text:
        return False

    try:
        resp = await send_private_msg(target, [{"type": "text", "data": {"text": typo}}],
                                      ws, want_response=True)
    except Exception:
        return False
    mid = (resp.get("data") or {}).get("message_id") if isinstance(resp, dict) else None
    if not mid:
        log_api("[撤回] 没拿到 message_id，跳过")
        return False

    await asyncio.sleep(1.5)
    await _send_or_queue("delete_msg", {"message_id": mid}, ws, "撤回")
    cfg.typo_history.append(now)
    log_system(f"打错字撤回: {typo[:12]} -> {text[:12]}")
    return True

# ===================== 重复回复拦截（v16.0.5） =====================
# 同一个对象短时间内收到两次一样的话，很出戏（「烦什么。」连问两遍）。
# 归一化后比较：去掉空格和标点，只比「说了什么」。

RECENT_REPLY_TTL = 180      # 3 分钟内的重复算重复
RECENT_REPLY_MIN_LEN = 3    # 太短的话（「嗯」「好」）不拦；3 字起才拦，否则「烦什么」漏掉
_recent_replies = {}        # target -> (normalized, ts)


def _normalize_reply(text):
    import re as _re
    return _re.sub(r"[\s\W_]+", "", text or "", flags=_re.UNICODE)


def is_duplicate_reply(target, text, now=None):
    """最近说过同样的话？返回 True 表示应该跳过"""
    import time as _t
    core = _normalize_reply(text)
    if len(core) < RECENT_REPLY_MIN_LEN:
        return False
    now = now or _t.time()
    last = _recent_replies.get(str(target))
    if last and now - last[1] < RECENT_REPLY_TTL and last[0] == core:
        return True
    _recent_replies[str(target)] = (core, now)
    return False