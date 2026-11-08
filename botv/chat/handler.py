# ===================== QQ 消息主循环 =====================
# 接收 → 解析 → 命令/表情包/AI → 发送
# 迁移自 handler.py（v5-R5）：入站解析已拆到 chat/inbound.py

import asyncio
import json
import os
import time as _time

from ..config import MASTER_QQ, LOCK_RELEASE_DELAY
from botv.core import state as cfg
from ..log import log_recv, log_err, log_system, log_api
from ..image import fetch_and_save_acg_image
from ..memory import extract_keywords, add_target_memory
from ..ai.client import get_character_reply
from ..commands import handle_command
from ..utils import make_image_msg
from ..ai.parse import parse_ai_reply
from ..core.types import Fallback  # 兜底文案标记（v5-F2）
from .send import send_short_reply, send_private_msg, send_sticker_private, send_sticker_group
from .inbound import parse_message_content, contains_sticker_key


async def websocket_handle_qq(ws):
    """WebSocket消息处理主函数：接收→解析→处理→回复"""
    async with cfg.active_ws_lock:  # 加锁，确保只有一个WebSocket连接
        if cfg.active_ws_qq and not getattr(cfg.active_ws_qq, "closed", False):  # 已有活跃连接
            await ws.close()  # 关闭新连接
            return  # 返回
        cfg.active_ws_qq = ws  # 设置当前活跃连接
    log_system("QQ上线(CLIP版)")  # 日志记录上线

    # 上线发文字 + ACG图片 检验连通性
    await send_short_reply(MASTER_QQ, "哼,上线了(叉腰)", ws, MASTER_QQ)  # 发送上线通知

    img_fp = await fetch_and_save_acg_image()  # 获取ACG图片
    if img_fp:
        img_fp = os.path.abspath(img_fp)  # 转为绝对路径
        log_api(f"[上线] ACG图片绝对路径: {img_fp}")  # 日志记录
        img_msg = make_image_msg(img_fp)  # 构建图片消息
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
            text = await parse_message_content(d.get("message", ""), uid)  # 解析消息内容
            if not text:  # 解析后文本为空
                continue  # 跳过

            # 代码模式：每次收到消息更新最后活跃时间戳
            if cfg.CODE_MODE:
                cfg.CODE_MODE_LAST_MSG_TIME = _time.time()

            async with cfg.PROCESS_LOCK:  # 加消息处理锁
                cfg.PROCESSED_MSG_IDS.append(mid)  # 记录已处理的消息ID
                log_recv(f"[QQ]{uid}:{text}")  # 日志记录接收
                tid = uid if mt == "private" else str(gid)  # 目标ID：私聊用QQ号，群聊用群号
                ck = extract_keywords(text)  # 提取关键词

                # 先检查是否是命令（仅主人有效）
                if await handle_command(text, uid, ws, mt == "group", gid):  # 是命令
                    pass  # 命令已处理，不再走AI回复
                elif contains_sticker_key(text):  # 包含表情包关键词
                    if mt == "group":  # 群聊
                        await send_sticker_group(gid, ws, uid)  # 发送群表情包
                    else:  # 私聊
                        await send_sticker_private(uid, ws, uid)  # 发送私聊表情包
                else:  # 普通对话
                    ans = await get_character_reply(text, tid, ck)  # 获取AI回复
                    target = gid if mt == "group" else uid  # 回复目标
                    if not ans or isinstance(ans, Fallback):
                        # v5-F2：兜底文案不是她的话——不进记忆、不进事件，只回一条中性的
                        log_api("[handler] 模型无回复或返回兜底，静默处理（不入库）")
                        await send_short_reply(target, "……", ws, uid, mt == "group", ck)
                    else:
                        dialog, action, img_kw, event, refined_kw = parse_ai_reply(ans)  # 解析AI回复
                        add_target_memory(tid, text, ans, img_kw, refined_kw, event)  # 保存记忆
                        await send_short_reply(target, ans, ws, uid, mt == "group", ck)  # 发送回复

                await asyncio.sleep(LOCK_RELEASE_DELAY)  # 锁释放延迟，防止消息处理过快
    except Exception as e:  # 捕获异常
        log_err(f"QQ异常:{e}")  # 日志记录异常
    finally:  # 清理
        async with cfg.active_ws_lock:  # 加锁
            if cfg.active_ws_qq is ws:  # 当前连接就是本连接
                cfg.active_ws_qq = None  # 清空活跃连接
        cfg.PROCESSED_MSG_IDS.clear()  # 清空已处理消息ID列表
        log_system("QQ断开")  # 日志记录断开
