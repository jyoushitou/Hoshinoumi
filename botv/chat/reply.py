# ===================== 回复组装 =====================
# 把模型输出（五行格式）变成可发送的消息片段列表：文本气泡 + 图片
# 迁移自 send.py（v5-R3），行为与迁移前完全一致
# 注意：这里只组装，不发送——发送在 chat/send.py

import os  # 路径处理

import botv.config as cfg  # 全局运行时变量（CODE_MODE）
from ..log import log_api  # 日志
from ..ai.parse import parse_ai_reply  # 解析AI回复
from ..image import get_best_image  # 图片搜索
from ..memory import extract_keywords  # 关键词提取


async def build_reply_message(txt, uid, kws=None):
    """构建回复消息列表：解析AI回复→文本+动作+图片，返回[(类型, 内容), ...]
        目标：AI回复只输出角色剧情内容（第一行对话+第二行动作）→ 两条独立QQ消息（两个气泡）+ 一张表情包
        标签、摘要、关键词仅用于内部搜图处理，禁止输出到对话"""
    dialog, action, img_kw, event, refined_kw = parse_ai_reply(txt)  # 解析AI回复
    log_api(f"[构建回复] dialog={dialog[:30]}, action={action[:20]}, img_kw={img_kw}")  # 日志记录
    parts = []  # 消息片段列表

    # ★ 不依赖 dialog 拼接结果（parse_ai_reply 可能将无标记行拼入 dialog）
    # 直接从原始文本拆出每一行 → 每一行 = 一条独立QQ消息（一个气泡）
    raw_lines = [l.strip() for l in txt.split('\n') if l.strip()]  # 去除空行后的所有行

    # 剥离可能的行号前缀（"第一行：""第二行："等），AI可能错误输出这些内部标记
    import re as _re
    def _strip_line_prefix(l):
        return _re.sub(r"^[第]{0,1}[一二三四五六七八九十0-9]{1,3}[行]：[\s　]*", "", l)
    raw_lines = [_strip_line_prefix(l) for l in raw_lines]

    # 第一行：对话内容 → 独立消息（气泡1）
    if len(raw_lines) >= 1 and raw_lines[0]:
        parts.append(("text", [{"type":"text","data":{"text":raw_lines[0]}}]))  # 气泡1
        log_api(f"[构建回复] 气泡1(对话): {raw_lines[0][:30]}")

    # 第二行：动作描写 → 独立消息（气泡2）
    # 严格固定结构：对话 → 动作 → 表情包，动作消息不允许缺失。
    # 若第二行缺失或是内部元数据（AI漏写动作行），自动补（无）兜底。
    _action_line = raw_lines[1] if len(raw_lines) >= 2 else ""
    _is_internal = _action_line.startswith(("关键词", "事件", "标签", "摘要", "动作", "描述", "提炼", "回复格式"))
    if _action_line and not _is_internal:
        parts.append(("text", [{"type":"text","data":{"text":_action_line}}]))  # 气泡2
        log_api(f"[构建回复] 气泡2(动作): {_action_line[:30]}")
    else:
        # AI漏写动作行 → 兜底补（无），保证动作消息永不缺失
        parts.append(("text", [{"type":"text","data":{"text":"（无）"}}]))  # 气泡2兜底
        log_api(f"[构建回复] 气泡2(动作)缺失({_action_line[:20]})，兜底补（无）")

    # 第三行及之后：标签、摘要、关键词提炼等内部元数据 → 仅用于内部搜图，禁止输出
    # 只输出角色剧情内容（对话+动作），后跟表情包
    internal_lines = raw_lines[2:]
    if internal_lines:
        log_api(f"[构建回复] 截留{len(internal_lines)}行内部元数据(关键词/事件摘要/关键词提炼)，禁止输出")

    # 代码模式：只发送文字不发送图片，保证完整详细的技术回答
    if cfg.CODE_MODE:
        log_api("[构建回复] 代码模式，跳过图片发送")
        return parts
    # 用第三行关键词选图，如果没有则用jieba从对话+动作中提取
    if img_kw:  # AI提供了图片关键词
        log_api(f"[构建回复] 按AI关键词搜图(20纬度): {img_kw}")  # 日志记录
        fp = await get_best_image(img_kw, uid)  # 按关键词搜图
        if fp:  # 搜到图片
            abs_fp = os.path.abspath(fp)  # 转为绝对路径（NapCat需要绝对路径）
            log_api(f"[构建回复] 搜到图片: {abs_fp}")  # 日志记录
            parts.append(("image", [{"type":"image","data":{"file":abs_fp}}]))  # 添加图片消息
        else:  # 20纬度都搜不到，立即用jieba兜底（不等1分钟）
            log_api(f"[构建回复] 20纬度均未搜到图，立即用jieba兜底")  # 日志记录
            search_kws = extract_keywords(f"{dialog} {action}")  # 用jieba从对话+动作中提取关键词
            if search_kws:
                log_api(f"[构建回复] jieba兜底关键词: {search_kws}")  # 日志记录
                fp2 = await get_best_image(search_kws, uid)  # 按jieba关键词搜图
                if fp2:
                    abs_fp2 = os.path.abspath(fp2)
                    log_api(f"[构建回复] jieba兜底搜到图片: {abs_fp2}")
                    parts.append(("image", [{"type":"image","data":{"file":abs_fp2}}]))
                else:
                    log_api(f"[构建回复] jieba兜底搜图也无结果")
            else:
                log_api(f"[构建回复] jieba兜底无关键词")
    else:  # img_kw为空，立即用jieba兜底
        log_api(f"[构建回复] img_kw为空，立即用jieba兜底")  # 日志记录
        search_kws = extract_keywords(f"{dialog} {action}")  # 用jieba从对话+动作中提取关键词
        if search_kws:
            log_api(f"[构建回复] jieba兜底关键词: {search_kws}")  # 日志记录
            fp = await get_best_image(search_kws, uid)  # 按jieba关键词搜图
            if fp:
                abs_fp = os.path.abspath(fp)
                log_api(f"[构建回复] jieba兜底搜到图片: {abs_fp}")
                parts.append(("image", [{"type":"image","data":{"file":abs_fp}}]))
            else:
                log_api(f"[构建回复] jieba兜底搜图也无结果")
        else:
            log_api(f"[构建回复] jieba兜底无关键词")
    return parts  # 返回消息片段列表
