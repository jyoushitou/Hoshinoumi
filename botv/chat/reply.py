# ===================== 回复组装 =====================
# 把模型输出变成可发送的消息片段列表：文本气泡 + 图片
#
# v5-F1/F3 修复：
#   1) 元数据改为「按标记」识别（关键词搜索图片用 / 事件摘要 / 关键词提炼），
#      不再按行号取前两行——多行对话与代码答案不会再被吞
#   2) 没有动作就不发「（无）」气泡
#   3) 代码模式整段发送，不拆气泡，代码块保持完整

import os  # 路径处理

from botv.core import state as cfg  # 运行时状态（CODE_MODE）
from ..log import log_api  # 日志
from ..ai.parse import parse_ai_reply  # 解析AI回复（取图片关键词）
from ..image import get_best_image, materialize_image  # 图片搜索 / 路径解析
from ..memory import extract_keywords  # 关键词提取

# 出现这些标记的行，以及它之后的所有行，都算内部元数据
META_MARKERS = ("关键词搜索图片用", "事件摘要", "关键词提炼", "标签：", "标签:")

# 单轮最多几条气泡：不是风格上限，只是模型格式崩了时的兜底（v6-A12）
MAX_REPLY_LINES = 10


def _strip_line_prefix(line):
    """剥离 AI 偶尔输出的「第一行：」「第二行：」前缀"""
    import re
    return re.sub(r"^[第]{0,1}[一二三四五六七八九十0-9]{1,3}[行]：[\s　]*", "", line)


def _is_action_line(line):
    """动作行：以括号开头、且足够短（避免把「（笑）今天…」这种长句当动作）"""
    if not line.startswith(("（", "(")):
        return False
    return len(line) <= 30


def split_reply_text(txt):
    """按标记把回复切成 (对话行列表, 动作, 元数据行列表)

    规则：
      - 遇到元数据标记 → 从该行起全部归入 meta
      - 元数据之前：唯一一条「括号开头的短句」算动作，其余全是对话
    """
    raw = [l.strip() for l in (txt or "").split("\n") if l.strip()]
    raw = [_strip_line_prefix(l) for l in raw]

    body, meta, in_meta = [], [], False
    for line in raw:
        if any(m in line for m in META_MARKERS):
            in_meta = True
        if in_meta:
            meta.append(line)
        else:
            body.append(line)

    dialog_lines, action = [], ""
    for line in body:
        if not action and _is_action_line(line):
            action = line
        else:
            dialog_lines.append(line)
    return dialog_lines, action, meta


async def build_reply_message(txt, uid, kws=None, is_group=False):
    """构建回复消息列表，返回 [(类型, 消息段列表), ...]"""
    dialog_lines, action, meta = split_reply_text(txt)
    dialog = "\n".join(dialog_lines)
    log_api(f"[构建回复] dialog={dialog[:30]!r}, action={action[:20]!r}, meta={len(meta)}行")

    parts = []  # 消息片段列表

    # ---- 代码模式：整段发一条，不拆气泡，代码块保持完整 ----
    if cfg.CODE_MODE:
        text = "\n".join(dialog_lines + ([action] if action else []))
        if text:
            parts.append(("text", [{"type": "text", "data": {"text": text}}]))
            log_api(f"[构建回复] 代码模式整段发送（{len(text)}字）")
        return parts

    # ---- 普通模式：一行一个气泡，行数由模型决定（v6-A12）----
    lines = list(dialog_lines)
    if action:
        lines.append(action)  # 动作也单独一条

    if len(lines) > MAX_REPLY_LINES:  # 异常保护：不是常规上限，只在模型失控时兜一下
        log_api(f"[构建回复] 回复行数异常({len(lines)})，尾部合并为一条")
        head = lines[:MAX_REPLY_LINES - 1]
        tail = "\n".join(lines[MAX_REPLY_LINES - 1:])
        lines = head + [tail]

    for i, line in enumerate(lines, 1):
        parts.append(("text", [{"type": "text", "data": {"text": line}}]))
        log_api(f"[构建回复] 气泡{i}: {line[:30]}")

    # ---- 选图：AI 给的关键词优先，否则 jieba 兜底 ----
    parsed = parse_ai_reply(txt)
    img_kw = parsed[2] if parsed else []

    def _image_part(path):
        """把路径变成消息段；解析不到（文件缺失）就返回 None，不发坏路径"""
        real = materialize_image(path)
        if not real:
            return None
        return ("image", [{"type": "image", "data": {"file": real}}])

    # v14-B1：整条回复只掷一次骰——AI 关键词和 jieba 兜底共用这个结果
    allow_image = image_allowed(uid, is_group)

    if img_kw and allow_image:
        fp = await get_best_image(img_kw, uid)
        part = _image_part(fp) if fp else None
        if part:
            parts.append(part)
            return parts
        log_api("[构建回复] AI 关键词未搜到图，改用 jieba 兜底")

    if not allow_image:
        log_api("[构建回复] 这次不配图（概率/冷却）")
        return parts

    search_kws = extract_keywords(f"{dialog} {action}")
    if search_kws:
        fp = await get_best_image(search_kws, uid)
        part = _image_part(fp) if fp else None
        if part:
            parts.append(part)
        else:
            log_api("[构建回复] jieba 兜底也没搜到图")
    else:
        log_api("[构建回复] jieba 兜底无关键词")

    return parts

# ===================== 发图择时（v14-B1） =====================
# 不是每条回复都配图。AI 给了关键词、也搜到了图，还要过一道概率。

IMAGE_PROB = 0.30           # 私聊基础概率
IMAGE_PROB_GROUP = 0.20     # 群里更保守
IMAGE_COOLDOWN = 600        # 同一个人 10 分钟最多一张
_last_image_ts = {}


def image_allowed(target, is_group=False, rng=None):
    """这次要不要配图（会记账）"""
    import random as _r
    import time as _t
    rng = rng or _r
    now = _t.time()
    if now - _last_image_ts.get(str(target), 0.0) < IMAGE_COOLDOWN:
        return False

    prob = IMAGE_PROB_GROUP if is_group else IMAGE_PROB
    try:
        from ..life.state import current as life_current
        if float(life_current().get("mood", 0.0)) < -0.2:
            prob *= 0.5  # 心情差时几乎不配图
    except Exception:
        pass

    if rng.random() > prob:
        return False
    _last_image_ts[str(target)] = now
    return True