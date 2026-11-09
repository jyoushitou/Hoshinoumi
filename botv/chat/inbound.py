# ===================== 入站消息解析 =====================
# 把 NapCat 的消息段（text / image / face）转成文本
# 迁移自 handler.py（v5-R5），逻辑逐字未改

import asyncio

from botv.core import state as cfg
from ..log import log_api
from ..image import process_and_save_image
from ..infra.repo_memory import add_event_to_db  # v11-A9：图片记忆
from ..ai.vision import describe_image  # v11-A8：直接看图
from ..image.store import update_image_tags
from ..utils import download_url


def contains_sticker_key(text):
    """检查文本是否包含表情包触发关键词"""
    for kw in cfg.STICKER_KEYWORDS:  # 遍历表情包关键词列表
        if kw in text:  # 文本包含该关键词
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


async def parse_message_content(raw_content, user_id):
    """解析消息内容：提取文本、处理图片、记录表情

    v8：返回 (文本, 图片 md5 列表)——md5 用来在回复后补标签。
    """
    input_text = ""  # 最终文本
    img_info = []  # 图片信息列表
    img_md5s = []  # 本条消息里的图片 md5
    if isinstance(raw_content, list):  # 消息是数组格式（包含多种类型）
        for item in raw_content:  # 遍历消息片段
            t = item.get("type")  # 消息类型
            d = item.get("data", {})  # 消息数据
            if t == "text":  # 文本类型
                input_text += d.get("text", "")  # 追加文本
            elif t == "image":  # 图片类型
                url = d.get("url") or d.get("file")  # 获取图片URL
                log_api(f"[消息解析] 收到图片: {url[:60]}")  # 日志记录
                img_data = await asyncio.to_thread(download_url, url)  # 下载图片（丢线程，别卡事件循环）
                if img_data:  # 下载成功
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
                        input_text += " " + desc
                    elif tags_str:
                        tag_list = tags_str.split(",")
                        img_info.append(f"[{tag_list[0]}]")
                        input_text += " " + " ".join(tag_list[:5])
                else:  # 下载失败
                    img_info.append("[图]")  # 添加通用图片标识
                    log_api(f"[消息解析] 图片下载失败: {url[:60]}")  # 日志记录
            elif t == "face":  # QQ表情类型
                fid = str(d.get("id"))  # 获取表情ID
                if fid:  # 表情ID有效
                    cfg.USER_STICKER_CACHE[user_id].append(fid)  # 缓存用户最近使用的表情
                    if len(cfg.USER_STICKER_CACHE[user_id]) > 20:  # 缓存超过20个
                        cfg.USER_STICKER_CACHE[user_id].pop(0)  # 移除最旧的
                img_info.append(f"[表情{fid}]")  # 添加表情标识
    else:  # 消息是纯文本
        input_text = str(raw_content).strip()  # 直接转为字符串
    if img_info:  # 有图片/表情信息
        input_text = f"{input_text} {' '.join(img_info)}"  # 追加到文本末尾
    log_api(f"[消息解析] 最终文本: {input_text[:60]}")  # 日志记录
    return input_text.strip(), img_md5s  # (文本, 图片md5列表)
