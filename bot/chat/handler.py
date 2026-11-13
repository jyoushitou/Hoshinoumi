# ===================== QQ 消息主循环 =====================
# 接收 → 解析 → 命令/表情包/AI → 发送
# 迁移自 handler.py（v5-R5）：入站解析已拆到 chat/inbound.py

import asyncio
import json
import os
import random
import time as _time
from collections import deque

from ..config import MASTER_QQ, LOCK_RELEASE_DELAY
from bot.core import state as cfg
from ..log import log_recv, log_err, log_system, log_api
from ..image.store import update_image_tags  # 图片标签回写（v8）
from ..image import fetch_and_save_acg_image
from ..memory import extract_keywords, add_target_memory
from ..ai.client import get_character_reply
from ..commands import handle_command, normalize_command
from ..utils import make_image_msg
from ..ai.parse import parse_ai_reply
from ..core.types import Fallback  # 兜底文案标记（v5-F2）
from .send import send_short_reply, send_private_msg, send_sticker_private, send_sticker_group, flush_outbox
from .inbound import parse_message_content, contains_sticker_key, is_at_me
from .timing import reply_delay
from ..core.locks import get_target_lock
from ..core import tunables, metrics
from ..life.impulse import note_user_message  # v10-U9
from ..life import pending as life_pending  # v10-U9b
from ..life import agenda as life_agenda  # v10-U10
from ..life import habit as life_habit  # v12-A17
from ..life import friction as life_friction  # v13-U20
from ..life import reading as life_reading  # v16：点名看书
from ..life import novel as life_novel  # v16：按书名搜索
from .notice import handle_notice  # v12-A16
from .cache import remember as remember_message  # v18.6：最近消息缓存

# v18.6：后台消息任务集合（避免 create_task 被 GC）
_bg_tasks = set()


def _sender_name(d):
    """取说话人昵称/群名片，缓存和引用块用"""
    s = d.get("sender") or {}
    return (s.get("card") or s.get("nickname") or str(d.get("user_id") or "")).strip()


def _looks_like_command(d):
    """命令走同步路径；只有主人发的才算"""
    if str(d.get("user_id")) != str(MASTER_QQ):
        return False
    msg = d.get("message")
    if isinstance(msg, str):
        return msg.lstrip()[:1] in ("!", "！")
    for seg in msg or []:
        if isinstance(seg, dict) and seg.get("type") == "text":
            text = (seg.get("data") or {}).get("text", "")
            return text.lstrip()[:1] in ("!", "！")
    return False


def _bg_done(task):
    _bg_tasks.discard(task)
    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        log_err(f"[消息] 后台处理失败: {e}")


def _dispatch_message(d, ws):
    """v18.6 U1：普通消息起独立任务，recv 循环不再被模型/get_msg 堵住"""
    if os.getenv("NAO_ASYNC_DISPATCH", "1") in ("0", "false", "False"):
        return _handle_message(d, ws)
    task = asyncio.create_task(_handle_message(d, ws))
    _bg_tasks.add(task)
    task.add_done_callback(_bg_done)
    return None

# ===================== 群聊节奏（v6-E29 / v10） =====================
GROUP_COOLDOWN = 20        # 同一个群两条回复的最小间隔（秒）
GROUP_WINDOW = 60          # 统计窗口（秒）
GROUP_WINDOW_MAX = 6       # 窗口内最多回几条
GROUP_AT_MIN_GAP = 3       # 被 @ 时也至少隔 3 秒，防连点
GROUP_SILENCE_PROB = 0.05  # 闸门放行后，仍有概率选择沉默（v6-A19）

# v10：群聊回话概率受全局状态影响（她是一个人，状态不分群）
GROUP_BASE_PROB = 0.20     # 基础概率：1/5
GROUP_PROB_MIN = 0.05
GROUP_PROB_MAX = 0.45
GROUP_LONELY_SPAN = 0.30   # 孤独每高出 0.3，概率 +0.09
GROUP_UNANSWERED_LIMIT = 3  # 连着说 3 句没人接
GROUP_UNANSWERED_DECAY = 0.5  # 概率减半


def group_reply_probability(state=None, streak=0):
    """群聊回话概率：孤独越高越想聊，心情差就少说，连着没人接再减半"""
    if state is None:
        try:
            from ..life.state import current as life_current
            state = life_current()
        except Exception:
            state = {}
    lonely = float(state.get("lonely", 0.2))
    mood = float(state.get("mood", 0.1))

    from ..core import tunables
    p = tunables.get("group_base_prob", GROUP_BASE_PROB) + max(0.0, lonely - 0.4) * GROUP_LONELY_SPAN
    if mood < -0.2:
        p *= 0.7          # 心情差，不想掺和
    elif mood > 0.4:
        p *= 1.1          # 心情好，愿意搭话
    if streak >= GROUP_UNANSWERED_LIMIT:
        p *= GROUP_UNANSWERED_DECAY
    return max(GROUP_PROB_MIN, min(GROUP_PROB_MAX, p))


def should_answer_group(gid, addressed):
    """这次该不该在群里接话，返回 (bool, 原因)

    用「这个群最近 60 秒收过几条」当社交频率，不做每轮配额。
    """
    now = _time.time()
    win = cfg.group_msg_window.setdefault(gid, deque(maxlen=30))
    while win and now - win[0] > GROUP_WINDOW:
        win.popleft()

    if len(win) >= GROUP_WINDOW_MAX:
        return False, f"{GROUP_WINDOW}秒内已回{len(win)}条"

    last = cfg.group_last_reply_ts.get(gid, 0)
    if addressed:
        if now - last < GROUP_AT_MIN_GAP:
            return False, "刚回过"
        # v14-B4：被 @ 也要掷骰——基础 75%，心情极差时降到 40%
        streak = cfg.group_streak.get(gid, 0)
        p = max(tunables.get("group_mention_prob", 0.75), group_reply_probability(streak=streak))
        try:
            from ..life.state import current as life_current
            if float(life_current().get("mood", 0.0)) < -0.6:
                p = 0.40
        except Exception:
            pass
        if random.random() > p:
            return False, f"被@{p:.0%}没回"
        return True, f"被@(p={p:.0%})"

    if now - last < GROUP_COOLDOWN:
        return False, f"冷却中({int(GROUP_COOLDOWN - (now - last))}秒)"

    # v10：概率由全局状态决定，连着没人接再打折
    streak = cfg.group_streak.get(gid, 0)
    p = group_reply_probability(streak=streak)
    if random.random() > p:
        return False, f"没命中接话概率(p={p:.0%})"
    return True, f"随机接话(p={p:.0%})"


def note_group_reply(gid):
    """记录一次群回复，供下次判断"""
    now = _time.time()
    cfg.group_last_reply_ts[gid] = now
    cfg.group_msg_window.setdefault(gid, deque(maxlen=30)).append(now)
    cfg.group_streak[gid] = cfg.group_streak.get(gid, 0) + 1  # 连着说了几句

# v5-F5：上线通知的冷却时间（秒）——重连太频繁时不重复打扰
ONLINE_NOTICE_COOLDOWN = 60


# ===================== 分享欲（v12-A18） =====================
# 不是每句都为了回应。偶尔多说一句「对了，今天…」。

SHARE_PROB = 0.06        # 每条回复后有 6% 概率多说一句
SHARE_COOLDOWN = 2400    # 同一个人 40 分钟内最多分享一次
_last_share_ts = {}


async def maybe_share_something(tid, ws):
    """按概率补一句自己的事；返回是否发了"""
    if random.random() > SHARE_PROB:
        return False
    now = _time.time()
    if now - _last_share_ts.get(tid, 0.0) < SHARE_COOLDOWN:
        return False
    try:
        from ..infra.repo_memory import load_today_life
        events = load_today_life()
    except Exception:
        events = []
    if not events:
        return False

    seed = random.choice(events)
    try:
        rep = await get_character_reply(
            f"（不用说别的。就说一句你今天的事：{seed}。"
            f"像突然想起来的，别问他问题）", tid)
    except Exception:
        return False
    if not rep:
        return False
    await send_short_reply(tid, rep, ws, tid, False, None)
    _last_share_ts[tid] = now
    log_system(f"分享欲: {str(seed)[:20]}")
    return True

def claim_online_notice():
    """决定这次连接要不要发上线通知（60 秒内只发一次）"""
    now = _time.time()
    if now - cfg.last_online_notice_ts < ONLINE_NOTICE_COOLDOWN:
        return False
    cfg.last_online_notice_ts = now
    return True


async def _reply_and_send(d, ws, text, img_md5s=None):
    """生成回复并发送（v17.3：从 _handle_message 抽出来，便于连发后统一回一次）"""
    mt = d.get("message_type")
    uid = str(d.get("user_id"))
    gid = d.get("group_id", 0)
    mid = d.get("message_id")
    addressed = is_at_me(d.get("message", ""), cfg.self_qq)
    tid = uid if mt == "private" else str(gid)
    ck = extract_keywords(text)

    async with get_target_lock(tid):
        cfg.PROCESSED_MSG_IDS.append(mid)  # 记录已处理的消息ID
        log_recv(f"[QQ]{uid}:{text}")  # 日志记录接收
        ck = extract_keywords(text)  # 提取关键词
        pending = None  # 待发送内容（锁外延迟发送，v6-A1）

        # v6-E29：群聊先过节奏闸门（命令不受限）
        if mt == "group" and not text.startswith("!"):
            ok, why = should_answer_group(gid, addressed)
            if not ok:
                log_api(f"[群聊] 跳过 {gid}: {why}")
                try:
                    from ..core import metrics
                    metrics.inc("group_skip")
                except Exception:
                    pass
                await asyncio.sleep(LOCK_RELEASE_DELAY)
                return
            log_api(f"[群聊] 接话 {gid}: {why}")
            try:
                from ..core import metrics
                metrics.inc("group_answer")
            except Exception:
                pass
            if not addressed and random.random() < GROUP_SILENCE_PROB:  # v6-A19：偶尔选择沉默
                log_api(f"[群聊] 这次选择沉默 {gid}")
                await asyncio.sleep(LOCK_RELEASE_DELAY)
                return

        # 先检查是否是命令（仅主人有效，立即回复不走延迟）
        if await handle_command(text, uid, ws, mt == "group", gid):  # 是命令
            pass  # 命令已处理，不再走AI回复
        elif contains_sticker_key(text):  # 包含表情包关键词
            pending = ("sticker", text)
        else:  # 普通对话
            target = gid if mt == "group" else uid  # 回复目标
            # v16：主人点名要她去看某本书 → 不走模型，直接应下
            _req = None
            try:
                _req = life_reading.detect_book_request(text)
            except Exception:
                _req = None
            ans = None
            if _req:
                try:
                    _reply = await life_reading.follow_request(uid, _req, search=life_novel.search_book)
                except Exception as _e:
                    log_api(f"[读书] 点名处理失败: {_e}")
                    _reply = "我记下了，等会儿去翻"
                pending = ("reply", target, _reply, mt == "group")
                # v17.9：答应了就得真读——后台读一章，读完补一句
                try:
                    asyncio.create_task(_read_after_request(uid, ws))
                except Exception as _e:
                    log_api(f"[读书] 后台读书启动失败: {_e}")
            else:
                ans = await get_character_reply(text, tid, ck,
                                        speaker=uid,
                                        is_group=(mt == "group"))  # 获取AI回复
            if _req:
                pass  # v16：点名已处理，不再走模型分支
            elif not ans or isinstance(ans, Fallback):
                # v5-F2：兜底文案不是她的话——不进记忆、不进事件，只回一条中性的
                log_api("[handler] 模型无回复或返回兜底，静默处理（不入库）")
                pending = ("reply", target, "……", mt == "group")
            else:
                dialog, action, img_kw, event, refined_kw = parse_ai_reply(ans)  # 解析AI回复
                add_target_memory(tid, text, ans, img_kw, refined_kw, event)  # 保存记忆
                if img_md5s and refined_kw:  # v8：用 AI 关键词回写图片标签
                    update_image_tags(img_md5s, refined_kw)
                pending = ("reply", target, ans, mt == "group")

        await asyncio.sleep(LOCK_RELEASE_DELAY)  # 锁释放延迟，防止消息处理过快

    # ===================== 锁外：延迟 + 发送（v6-A1） =====================
    if pending and pending[0] == "sticker":
        if mt == "group":
            await send_sticker_group(gid, ws, uid, text)
        else:
            await send_sticker_private(uid, ws, uid, text)
    elif pending:
        _, target, reply_text, is_group = pending
        delay = reply_delay()  # 按时段 + 随机
        log_api(f"[延迟] {delay:.1f} 秒后回复 {target}")
        await asyncio.sleep(delay)
        # v13-G47：偶尔欲言又止
        try:
            modified = life_friction.maybe_trail_off(reply_text)
            if modified != reply_text:
                log_api("[摩擦] 欲言又止")
                reply_text = modified
                pending = ("reply", target, reply_text, is_group)
        except Exception:
            pass

        # v12-A13：小概率先「手滑」一次
        if not is_group:
            try:
                from ..chat.send import try_typo_recall
                first_line = (reply_text or "").split("\n")[0]
                await try_typo_recall(target, first_line, ws)
            except Exception:
                pass

        from ..chat.send import send_segmented_reply
        await send_segmented_reply(target, reply_text, ws, uid, is_group, ck)
        try:
            from ..core import metrics
            metrics.inc("replies")
        except Exception:
            pass
        if is_group:  # v6-E29：记录这次群回复
            note_group_reply(gid)
        else:
            try:  # v12-A18：偶尔补一句自己的事
                await maybe_share_something(target, ws)
            except Exception:
                pass

async def _read_after_request(uid, ws):
    """点名之后真的读一章，读完回一句（失败也说明原因）"""
    from ..life import novel as life_novel
    from ..life import reading as life_reading

    try:
        out = await life_reading.read_for_request(
            str(uid), life_novel.fetch_book, life_novel.fetch_chapter,
            life_reading.summarize_chapter)
    except Exception as e:
        log_api(f"[读书] 后台读书异常: {e}")
        return

    try:
        if out.get("ok"):
            rep = (f"看完了《{out.get('chapter')}》。{out.get('summary') or ''}").strip()
        else:
            rep = f"没读成：{out.get('reason') or '原因不明'}"
        from .send import send_short_reply
        await send_short_reply(str(uid), rep[:400], ws, str(uid), False, None)
    except Exception as e:
        log_api(f"[读书] 结果发送失败: {e}")


async def _handle_message(d, ws):
    """处理一条消息（v17.3 U1：从接收循环里抽出来，便于以后投递/合并）"""

    mt = d.get("message_type")  # 消息类型：private/group
    mid = d.get("message_id")  # 消息ID
    if not mid or mid in cfg.PROCESSED_MSG_IDS:  # 消息ID无效或已处理
        return  # 跳过
    uid = str(d.get("user_id"))  # 用户QQ号
    gid = d.get("group_id", 0)  # 群号（私聊为0）
    # v6-E29：记录机器人自己的QQ号，用于判断是否被 @
    self_qq = d.get("self_id")
    if self_qq:
        cfg.self_qq = self_qq
    addressed = is_at_me(d.get("message", ""), cfg.self_qq)
    text, img_md5s = await parse_message_content(d.get("message", ""), uid, ws)  # (文本, 图片md5)
    text = normalize_command(text)  # v18.20：全角 ! 也能当命令
    remember_message(mid, _sender_name(d), text)  # v18.6：入站消息进缓存，引用可零延迟命中
    note_user_message()  # v10-U9：她在等你，别急着主动找
    try:
        life_habit.learn(uid, text)  # v12-A17：学一点他的口头禅
    except Exception:
        pass
    try:  # v13：他说软话就哄好，否则只记录和好进度
        if life_friction.is_sorry(text):
            life_friction.apologize(uid)
        life_friction.on_user_message(uid)
    except Exception:
        pass
    try:
        for it in life_pending.detect(text):  # v10-U9b：记下承诺/时间锚点
            life_pending.add([it])
    except Exception:
        pass
    try:
        ev = life_agenda.extract(text)  # v10-U10：时间 + 事件 → 日程
        if ev:
            life_agenda.add(ev)
    except Exception:
        pass
    if mt == "group" and addressed:
        cfg.group_streak[gid] = 0  # v10：有人点她名，连说计数清零
    if not text:  # 解析后文本为空
        return  # 跳过

    # v19.1：短期对话流（群聊只记与机器人相关的消息）
    if mt == "private" or addressed:
        try:
            from ..infra import repo_conversation
            _tid = uid if mt == "private" else str(gid)
            repo_conversation.append(
                target_id=_tid, content=text, role="user", channel="qq",
                thread_id=f"qq:{mt}:{_tid}", message_id=mid,
                meta={"images": img_md5s} if img_md5s else None,
            )
        except Exception as _e:
            log_api(f"[对话] 写入失败（忽略）: {_e}")

    # v18.3 U2：从对话里抽事实卡（只私聊 + 只主人）
    try:
        from ..life import facts as facts_mod

        if True:  # v18.4：任何人的事实都记（按说话人隔离）
            _fs = facts_mod.extract(text)
            if _fs:
                n = facts_mod.remember(uid, _fs)
                if n:
                    log_system(f"[事实] 记住 {n} 条："
                               + "；".join(facts_mod.describe(f) for f in _fs))
    except Exception as _e:
        log_api(f"[事实] 提取失败（忽略）: {_e}")

    # v17.7：从对话里提取定时任务（只私聊 + 只主人）
    try:
        from ..schedule import extract as extract_mod
        if extract_mod.should_extract(mt, text, uid, cfg.MASTER_QQ):
            _tid, _data = extract_mod.create_from_text(text, uid)
            if _data and (_tid or _data.get("override_scene")):
                label = (f"#{_tid}" if _tid else
                         f"当天微调 {_data.get('override_scene')}")
                log_system(f"[定时] {label}：{_data.get('content')}")
                try:
                    from ..chat.send import send_short_reply
                    await send_short_reply(uid, extract_mod.describe(_data, _tid or 0),
                                           ws, uid, False, None)
                except Exception as _e:
                    log_api(f"[定时] 确认回复失败（忽略）: {_e}")
    except Exception as _e:
        log_api(f"[定时] 提取失败（忽略）: {_e}")

    # 代码模式：每次收到消息更新最后活跃时间戳
    if cfg.CODE_MODE:
        cfg.CODE_MODE_LAST_MSG_TIME = _time.time()

    tid = uid if mt == "private" else str(gid)  # 目标ID：私聊用QQ号，群聊用群号

    # v17.3 U2：连发合并——同一个人连发几句，只回一次
    from .batcher import batchable, get_batcher, set_handler
    set_handler(_reply_and_send)
    if batchable(mt, text):
        await get_batcher().offer(tid, (d, ws, text, img_md5s))
        return

    # v6-E26：按对象加锁——同一个人串行，不同的人可以并行（5 路对话）
    await _reply_and_send(d, ws, text, img_md5s)


async def websocket_handle_qq(ws):
    """WebSocket消息处理主函数：接收→解析→处理→回复"""
    async with cfg.active_ws_lock:  # 加锁，确保只有一个WebSocket连接
        if cfg.active_ws_qq and not getattr(cfg.active_ws_qq, "closed", False):  # 已有活跃连接
            await ws.close()  # 关闭新连接
            return  # 返回
        cfg.active_ws_qq = ws  # 设置当前活跃连接
    log_system("QQ上线")  # 日志记录上线

    # v5-F6：先把断线期间积压的消息补发出去
    if cfg.pending_outbox:
        log_system(f"发现 {len(cfg.pending_outbox)} 条断线消息，开始补发")
    try:
        sent = await flush_outbox(ws)
        if cfg.pending_outbox:
            log_err(f"补发后仍有 {len(cfg.pending_outbox)} 条没发出去")
        elif sent:
            log_system(f"断线消息已全部补发（{sent} 条）")
    except Exception as e:
        log_err(f"补发队列异常: {e}")

    # v5-F5：60 秒内只发一次上线通知，避免重连刷屏
    if not claim_online_notice():
        log_system("QQ重连（60秒内已发过上线通知，跳过通知与配图）")
    else:
        # 上线发文字 + ACG图片 检验连通性
        await send_short_reply(MASTER_QQ, "哼,上线了(叉腰)", ws, MASTER_QQ)  # 发送上线通知

        img_fp = await fetch_and_save_acg_image()  # 获取ACG图片
        if img_fp:
            log_api(f"[上线] ACG图片: {img_fp}")  # 日志记录
            img_msg = make_image_msg(img_fp)  # 构建图片消息（内部已解析路径）
            if img_msg and not getattr(ws, "closed", False):  # 图片有效且连接未关闭
                await send_private_msg(MASTER_QQ, img_msg, ws)  # 发送图片给主人
                log_system("上线ACG图片已发送")  # 日志记录
        else:
            log_api("[上线] ACG图片获取失败")  # 日志记录

    try:
        while True:  # 消息接收循环
            raw = await ws.recv()  # 接收原始消息
            rs = raw.decode("utf-8", "ignore") if isinstance(raw, bytes) else raw  # 解码字节为字符串
            d = json.loads(rs)  # 解析JSON

            # v12-A13：带 echo 的是 NapCat 的响应包，不是新消息
            if isinstance(d, dict) and d.get("echo"):
                _fut = cfg.pending_echo.pop(d["echo"], None)
                if _fut and not _fut.done():
                    _fut.set_result(d)
                continue

            # v12-A16：通知事件（戳一戳等）
            if isinstance(d, dict) and d.get("post_type") == "notice":
                try:
                    from .send import _send_or_queue
                    self_qq = d.get("self_id") or cfg.self_qq
                    await handle_notice(d, ws, self_qq, _send_or_queue)
                except Exception as e:
                    log_api(f"[通知] 处理失败: {e}")
                continue
            if _looks_like_command(d):
                await _handle_message(d, ws)  # 命令保持同步，别排在模型后面
            else:
                _coro = _dispatch_message(d, ws)  # 普通消息并发，recv 循环继续读回包
                if _coro is not None:
                    await _coro              # NAO_ASYNC_DISPATCH=0 时退回串行
    except Exception as e:  # 捕获异常
        log_err(f"QQ异常:{e}")  # 日志记录异常
    finally:  # 清理
        for _t in list(_bg_tasks):
            _t.cancel()
        async with cfg.active_ws_lock:  # 加锁
            if cfg.active_ws_qq is ws:  # 当前连接就是本连接
                cfg.active_ws_qq = None  # 清空活跃连接
        cfg.PROCESSED_MSG_IDS.clear()  # 清空已处理消息ID列表
        log_system("QQ断开")  # 日志记录断开
