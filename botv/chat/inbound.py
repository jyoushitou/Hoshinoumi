# ===================== 入站消息解析 =====================
# 把 NapCat 的消息段（text / image / face）转成文本
# 迁移自 handler.py（v5-R5），逻辑逐字未改

import asyncio

from botv.core import state as cfg
from ..infra.blocking import run_blocking  # v17.0.3：阻塞调用统一入口
from ..log import log_api
from ..image import process_and_save_image
from ..infra.repo_memory import add_event_to_db  # v11-A9：图片记忆
from ..ai.vision import describe_image  # v11-A8：直接看图
from ..speech.asr import transcribe  # v11-A14：语音转文字
from ..image.store import update_image_tags
from ..core import metrics
import re

from ..utils import download_url
from .cache import get as get_cached_message, remember as remember_message

_CQ_RE = re.compile(r"\[CQ:([a-zA-Z]+)[^\]]*\]")


def _clean_quoted(text):
    """把引用原文里的 CQ 码换成类型位，压掉换行"""
    text = (text or "").strip()
    if not text:
        return ""
    type_map = {"image": "[图片]", "record": "[语音]", "face": "[表情]",
                "mface": "[表情]", "at": "@某人"}

    def _repl(m):
        return type_map.get(m.group(1).lower(), "")

    text = _CQ_RE.sub(_repl, text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _quote_detail(who, text):
    """引用块：带说话人 + 原话，最多 120 字"""
    text = _clean_quoted(text)
    if not text:
        return ""
    who = (who or "某人").strip()
    return f"【引用 {who}】原话：{text[:120]}"


def _quoted_text(data):
    """get_msg 回包里的原文：优先 raw_message，没有就拼 message 段"""
    raw = (data or {}).get("raw_message") or ""
    if not raw:
        segs = (data or {}).get("message")
        if isinstance(segs, list):
            raw = "".join(str((s.get("data") or {}).get("text", ""))
                          for s in segs if s.get("type") == "text")
    return _clean_quoted(raw)


def contains_sticker_key(text):
    """检查文本是否包含表情包触发关键词

    v17.9：先剥掉 [表情5] / [图] 这类占位符，否则「他发表情」会被当成
    「他要我发表情」，于是只回一个表情包、没有一句话。
    """
    import re

    # 纯表情消息被归一化成「（他发了个 QQ 表情…）」——这是“对方发表情”，
    # 不是“对方要求发表情”，不能走表情包快捷回复。
    if (text or "").lstrip().startswith("（他发了个 QQ 表情"):
        return False
    plain = re.sub(r"\[[^\]]{1,8}\]", "", text or "")
    for kw in cfg.STICKER_KEYWORDS:  # 遍历表情包关键词列表
        if kw in plain:  # 文本包含该关键词
            return True  # 返回True
    return False  # 不包含任何关键词


def is_at_me(raw_content, self_qq):
    """消息里是否 @ 了机器人自己（v6-E29）"""
    if not self_qq or not isinstance(raw_content, list):
        return False
    for item in raw_content:
        if item.get("type") == "at":
            if str(item.get("data", {}).get("qq")) == str(self_qq):
                return True
    return False


async def parse_message_content(raw_content, user_id, ws=None):
    """解析消息内容：提取文本、处理图片、记录表情

    v8：返回 (文本, 图片 md5 列表)——md5 用来在回复后补标签。
    """
    input_text = ""  # 最终文本
    img_info = []  # 图片信息列表
    img_md5s = []  # 本条消息里的图片 md5
    quote_block = ""  # v18.6：引用块，最后统一追加
    if isinstance(raw_content, list):  # 消息是数组格式（包含多种类型）
        for item in raw_content:  # 遍历消息片段
            t = item.get("type")  # 消息类型
            d = item.get("data", {})  # 消息数据
            if t == "text":  # 文本类型
                input_text += d.get("text", "")  # 追加文本
            elif t == "image":  # 图片类型
                url = d.get("url") or d.get("file")  # 获取图片URL
                log_api(f"[消息解析] 收到图片: {url[:60]}")  # 日志记录
                img_data = await run_blocking(download_url, url, timeout=60, name="image")  # v17.0.3：统一线程池
                if img_data:  # 下载成功
                    is_gif = img_data[:6] in (b"GIF89a", b"GIF87a")  # v11：动图只能看到一帧
                    md5, tags_str, fp = await process_and_save_image(img_data, url, user_id, keywords=["用户发图"])  # 先存下来
                    log_api(f"[消息解析] 图片处理结果: md5={md5}, tags={tags_str}, fp={fp}")

                    # v11-A8/A6：交给多模态模型看一眼，拿回描述 + 标签
                    desc, vt = None, []
                    try:
                        desc, vt = await describe_image(img_data)
                    except Exception as e:
                        log_api(f"[消息解析] 视觉失败: {e}")

                    if vt:
                        tags_str = ",".join(vt)
                        if md5:
                            try:
                                update_image_tags([md5], vt)
                            except Exception:
                                pass

                    if md5:
                        img_md5s.append(md5)
                        try:  # v11-A9：她记住「你发过一张什么样的图」
                            memo = f"发来一张图（{desc}）" if desc else f"发来一张图（{tags_str}）"
                            add_event_to_db(user_id, memo, tags=tags_str[:40],
                                            kind="photo", importance=2)
                        except Exception:
                            pass

                    if desc:  # 有描述就直接给模型「看到了什么」
                        img_info.append("[图]")
                        input_text += " " + desc + ("（这是一张动图，你只看到其中一帧）" if is_gif else "")
                    elif vt:  # 只有标签
                        img_info.append(f"[{vt[0]}]")
                        input_text += " " + " ".join(vt[:5])
                    else:  # v17.9：图收到了，只是没看清——别说成「没加载出来」
                        img_info.append("[图]")
                        input_text += " （他发了一张图，你看清了轮廓但说不出细节，别让他重发）"
                else:  # 下载失败
                    img_info.append("[图]")  # 添加通用图片标识
                    log_api(f"[消息解析] 图片下载失败: {url[:60]}")  # 日志记录
            elif t == "reply":  # 引用某条消息（v12-A15 / v18.6）
                quoted = d.get("id")
                detail = ""

                # 1) 先查最近消息缓存（零延迟）
                cached = get_cached_message(quoted)
                if cached:
                    who, text_q = cached
                    detail = _quote_detail(who, text_q)
                    if detail:
                        metrics.inc("quote_hit")

                # 2) 缓存没有才发 get_msg；超时压到 2 秒
                if not detail and quoted and ws is not None:
                    try:
                        from .send import request_action
                        resp = await request_action(
                            "get_msg", {"message_id": quoted}, ws, "取引用", timeout=2)
                        data = (resp or {}).get("data") or {}
                        text_q = _quoted_text(data)
                        who = ((data.get("sender") or {}).get("nickname") or "").strip()
                        if text_q:
                            detail = _quote_detail(who, text_q)
                            remember_message(quoted, who, text_q)
                            metrics.inc("quote_hit")
                    except asyncio.TimeoutError:
                        metrics.inc("quote_timeout")
                        detail = ""
                    except Exception:
                        detail = ""

                # 3) 还取不到就明说，别让模型装懂
                if not detail:
                    metrics.inc("quote_miss")
                    log_api(f"[引用] 未命中: {quoted}")
                    detail = "（他引用了一条较早的消息，你看不到，别装懂）"
                quote_block = detail

            elif t == "record":  # 语音条（v11-A14）
                url = d.get("url") or d.get("file")
                log_api(f"[消息解析] 收到语音: {str(url)[:60]}")
                audio = None
                if url:
                    try:
                        audio = await run_blocking(download_url, url, timeout=60, name="audio")  # v17.0.3
                    except Exception:
                        audio = None
                text = await transcribe(audio, url or "") if audio else None
                if text:
                    img_info.append("[语音]")
                    input_text += " " + text
                else:
                    img_info.append("[语音]")

            elif t == "face":  # QQ表情类型
                fid = str(d.get("id"))  # 获取表情ID
                if fid:  # 表情ID有效
                    cfg.USER_STICKER_CACHE[user_id].append(fid)  # 缓存用户最近使用的表情
                    if len(cfg.USER_STICKER_CACHE[user_id]) > 20:  # 缓存超过20个
                        cfg.USER_STICKER_CACHE[user_id].pop(0)  # 移除最旧的
                img_info.append(f"[表情{fid}]")  # 添加表情标识
    else:  # 消息是纯文本
        input_text = str(raw_content).strip()  # 直接转为字符串
    # v17.9：整条消息只有表情/占位符 → 换成一句人话，让模型正常接
    _plain = re.sub(r"\[[^\]]{1,8}\]", "", input_text).strip()
    if not _plain and img_info:
        if any(x.startswith("[表情") for x in img_info):
            input_text = "（他发了个 QQ 表情，没说话，你用一句话接住）"
            img_info = [x for x in img_info if not x.startswith("[表情")]
        elif "[图]" in img_info:
            input_text = "（他发了一张图，没说话）"
            img_info = [x for x in img_info if x != "[图]"]

    if img_info:  # 有图片/表情信息
        input_text = f"{input_text} {' '.join(img_info)}"  # 追加到文本末尾
    if quote_block:  # v18.6：引用块放最后，不污染关键词
        input_text = f"{input_text} {quote_block}"
    log_api(f"[消息解析] 最终文本: {input_text[:60]}")  # 日志记录
    return input_text.strip(), img_md5s  # (文本, 图片md5列表)
