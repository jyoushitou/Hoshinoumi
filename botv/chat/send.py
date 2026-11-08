# ===================== 消息发送 =====================
# 选图 + WebSocket 投递（v5-R4）
# 迁移自 botv/send.py：这里只负责「发」，组装在 chat/reply.py

import asyncio
import json
import os
import random

from ..config import STICKER_FACE_IDS, STICKER_ARCHIVE_DIR
from botv.core import state as cfg
from ..log import log_send, log_err, log_api, log_system
from ..image import search_local_image_by_tags, get_best_image
from ..memory import extract_keywords
from ..utils import encode_image_base64, make_image_msg
from ..db import get_cursor
from .reply import build_reply_message


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


async def _send_or_queue(action, params, ws, label):
    """发送一条消息；连接断了就入队，等重连补发"""
    payload = json.dumps({"action": action, "params": params}, ensure_ascii=False)
    if not _alive(ws):
        _enqueue(payload, label)
        return False
    async with cfg.send_lock:  # 加发送锁，防止并发发送
        try:
            await ws.send(payload)
            return True
        except Exception as e:
            log_err(f"{label}失败:{e}")
            _enqueue(payload, label)
            return False


async def flush_outbox(ws):
    """重连后补发断线期间积压的消息，返回补发条数"""
    if not _alive(ws) or not cfg.pending_outbox:
        return 0
    sent = 0
    while cfg.pending_outbox:
        payload = cfg.pending_outbox[0]
        try:
            async with cfg.send_lock:
                await ws.send(payload)
            cfg.pending_outbox.popleft()
            sent += 1
        except Exception as e:
            log_err(f"补发失败，保留队列: {e}")
            break
    if sent:
        log_system(f"断线消息补发完成: {sent} 条")
    return sent


async def send_private_msg(qq, msg, ws):
    """通过WebSocket发送私聊消息（断线自动入队）"""
    return await _send_or_queue("send_private_msg", {"user_id": qq, "message": msg}, ws, "私聊")


async def send_group_msg(gid, msg, ws):
    """通过WebSocket发送群聊消息（断线自动入队）"""
    return await _send_or_queue("send_group_msg", {"group_id": gid, "message": msg}, ws, "群聊")


async def send_short_reply(tid, text, ws, uid, is_group=False, kws=None):
    """发送完整回复：构建消息→逐条发送（文本+图片）"""
    parts = await build_reply_message(text, uid, kws)  # 构建回复消息列表
    log_api(f"[发送] 共{len(parts)}条消息: {[p[0] for p in parts]}")  # 日志记录消息数量
    for ptype, msg in parts:  # 遍历每条消息
        log_api(f"[发送] 类型={ptype}, 内容预览={str(msg)[:60]}")  # 日志记录
        if is_group:  # 群聊
            await send_group_msg(tid, msg, ws)  # 发送群消息
        else:  # 私聊
            await send_private_msg(tid, msg, ws)  # 发送私聊消息
        await asyncio.sleep(2.0)  # 每条间隔2秒，确保QQ识别为独立消息，一条一条发
    log_send(f"回复:{text[:40]}")  # 日志记录发送


async def send_sticker_private(qq, ws, uid):
    """发送私聊表情包"""
    s = select_best_sticker(uid)  # 选择最佳表情包
    if isinstance(s, str):  # 返回的是QQ表情ID（字符串）
        await send_private_msg(qq, [{"type":"face","data":{"id":s}}], ws)  # 发送QQ表情
    else:  # 返回的是文件路径
        img_msg = make_image_msg(s)  # 构建图片消息
        if img_msg:  # 构建成功
            await send_private_msg(qq, img_msg, ws)  # 发送图片


async def send_sticker_group(gid, ws, uid):
    """发送群聊表情包"""
    s = select_best_sticker(uid)  # 选择最佳表情包
    if isinstance(s, str):  # 返回的是QQ表情ID（字符串）
        await send_group_msg(gid, [{"type":"face","data":{"id":s}}], ws)  # 发送QQ表情
    else:  # 返回的是文件路径
        img_msg = make_image_msg(s)  # 构建图片消息
        if img_msg:  # 构建成功
            await send_group_msg(gid, img_msg, ws)  # 发送图片
