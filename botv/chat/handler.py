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
from botv.core import state as cfg
from ..log import log_recv, log_err, log_system, log_api
from ..image.store import update_image_tags  # 图片标签回写（v8）
from ..image import fetch_and_save_acg_image
from ..memory import extract_keywords, add_target_memory
from ..ai.client import get_character_reply
from ..commands import handle_command
from ..utils import make_image_msg
from ..ai.parse import parse_ai_reply
from ..core.types import Fallback  # 兜底文案标记（v5-F2）
from .send import send_short_reply, send_private_msg, send_sticker_private, send_sticker_group, flush_outbox
from .inbound import parse_message_content, contains_sticker_key, is_at_me
from .timing import reply_delay
from ..core.locks import get_target_lock
from ..life.impulse import note_user_message  # v10-U9

# ===================== 群聊节奏（v6-E29） =====================
GROUP_COOLDOWN = 20        # 同一个群两条回复的最小间隔（秒）
GROUP_WINDOW = 60          # 统计窗口（秒）
GROUP_WINDOW_MAX = 6       # 窗口内最多回几条
GROUP_REPLY_PROB = 1 / 3   # 没被 @ 时的接话概率
GROUP_AT_MIN_GAP = 3       # 被 @ 时也至少隔 3 秒，防连点
GROUP_SILENCE_PROB = 0.05  # 闸门放行后，仍有概率选择沉默（v6-A19）


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
        return True, "被@"

    if now - last < GROUP_COOLDOWN:
        return False, f"冷却中({int(GROUP_COOLDOWN - (now - last))}秒)"
    if random.random() > GROUP_REPLY_PROB:
        return False, "没命中接话概率"
    return True, "随机接话"


def note_group_reply(gid):
    """记录一次群回复，供下次判断"""
    now = _time.time()
    cfg.group_last_reply_ts[gid] = now
    cfg.group_msg_window.setdefault(gid, deque(maxlen=30)).append(now)

# v5-F5：上线通知的冷却时间（秒）——重连太频繁时不重复打扰
ONLINE_NOTICE_COOLDOWN = 60


def claim_online_notice():
    """决定这次连接要不要发上线通知（60 秒内只发一次）"""
    now = _time.time()
    if now - cfg.last_online_notice_ts < ONLINE_NOTICE_COOLDOWN:
        return False
    cfg.last_online_notice_ts = now
    return True


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
            mt = d.get("message_type")  # 消息类型：private/group
            mid = d.get("message_id")  # 消息ID
            if not mid or mid in cfg.PROCESSED_MSG_IDS:  # 消息ID无效或已处理
                continue  # 跳过
            uid = str(d.get("user_id"))  # 用户QQ号
            gid = d.get("group_id", 0)  # 群号（私聊为0）
            # v6-E29：记录机器人自己的QQ号，用于判断是否被 @
            self_qq = d.get("self_id")
            if self_qq:
                cfg.self_qq = self_qq
            addressed = is_at_me(d.get("message", ""), cfg.self_qq)
            text, img_md5s = await parse_message_content(d.get("message", ""), uid)  # (文本, 图片md5)
            note_user_message()  # v10-U9：她在等你，别急着主动找
            if not text:  # 解析后文本为空
                continue  # 跳过

            # 代码模式：每次收到消息更新最后活跃时间戳
            if cfg.CODE_MODE:
                cfg.CODE_MODE_LAST_MSG_TIME = _time.time()

            tid = uid if mt == "private" else str(gid)  # 目标ID：私聊用QQ号，群聊用群号
            # v6-E26：按对象加锁——同一个人串行，不同的人可以并行（5 路对话）
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
                        await asyncio.sleep(LOCK_RELEASE_DELAY)
                        continue
                    log_api(f"[群聊] 接话 {gid}: {why}")
                    if not addressed and random.random() < GROUP_SILENCE_PROB:  # v6-A19：偶尔选择沉默
                        log_api(f"[群聊] 这次选择沉默 {gid}")
                        await asyncio.sleep(LOCK_RELEASE_DELAY)
                        continue

                # 先检查是否是命令（仅主人有效，立即回复不走延迟）
                if await handle_command(text, uid, ws, mt == "group", gid):  # 是命令
                    pass  # 命令已处理，不再走AI回复
                elif contains_sticker_key(text):  # 包含表情包关键词
                    pending = ("sticker",)
                else:  # 普通对话
                    ans = await get_character_reply(text, tid, ck)  # 获取AI回复
                    target = gid if mt == "group" else uid  # 回复目标
                    if not ans or isinstance(ans, Fallback):
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
                    await send_sticker_group(gid, ws, uid)
                else:
                    await send_sticker_private(uid, ws, uid)
            elif pending:
                _, target, reply_text, is_group = pending
                delay = reply_delay()  # 按时段 + 随机
                log_api(f"[延迟] {delay:.1f} 秒后回复 {target}")
                await asyncio.sleep(delay)
                await send_short_reply(target, reply_text, ws, uid, is_group, ck)
                if is_group:  # v6-E29：记录这次群回复
                    note_group_reply(gid)
    except Exception as e:  # 捕获异常
        log_err(f"QQ异常:{e}")  # 日志记录异常
    finally:  # 清理
        async with cfg.active_ws_lock:  # 加锁
            if cfg.active_ws_qq is ws:  # 当前连接就是本连接
                cfg.active_ws_qq = None  # 清空活跃连接
        cfg.PROCESSED_MSG_IDS.clear()  # 清空已处理消息ID列表
        log_system("QQ断开")  # 日志记录断开
