# ===================== 视觉（v11-A8/A6） =====================
# 图片直接交给多模态模型，拿回「一句人话描述 + 几个标签」。
#
# 设计原则：**失败就当没有**。key 没开视觉、模型下线、网络超时——
# 一律返回 (None, [])，上层退回原来的「用聊天关键词当标签」。

import base64
import io
import os

import botv.core.state as cfg
from ..log import log_api

# 可用环境变量覆盖，默认用 DeepSeek 的视觉模型
DEFAULT_VISION_MODEL = os.getenv("NAO_VISION_MODEL", "deepseek-flash")
DEFAULT_VISION_URL = os.getenv("NAO_VISION_URL", "https://api.deepseek.com/v1/chat/completions")
MAX_SIDE = 1024
JPEG_QUALITY = 85

PROMPT = (
    "看这张图，用一句话说出你看到的（像朋友随口说的那样，别用「图片中」「这是一张」开头），"
    "再给 3~5 个关键词。\n"
    "严格按这个格式输出：\n"
    "描述：<一句话>\n"
    "标签：<词1,词2,词3>"
)


def compress_b64(img_bytes, max_side=MAX_SIDE, quality=JPEG_QUALITY):
    """压缩成 base64；PIL 不可用就原样编码"""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(img_bytes))
        im = im.convert("RGB")
        w, h = im.size
        if max(w, h) > max_side:
            ratio = max_side / float(max(w, h))
            im = im.resize((int(w * ratio), int(h * ratio)))
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=quality)
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return base64.b64encode(img_bytes).decode()


def parse_reply(text):
    """从模型输出里拆出 (描述, 标签列表)"""
    desc, tags = "", []
    for line in (text or "").splitlines():
        line = line.strip()
        if line.startswith("描述"):
            desc = line.split("：", 1)[-1].split(":", 1)[-1].strip()
        elif line.startswith("标签"):
            raw = line.split("：", 1)[-1].split(":", 1)[-1].strip()
            tags = [t.strip() for t in raw.replace("，", ",").split(",") if t.strip()]
    if not desc and not tags:
        # 模型没按格式来：整段当描述，不猜标签
        desc = (text or "").strip()[:60]
    return desc, tags[:5]


async def describe_image(img_bytes):
    """返回 (描述, 标签)；任何失败都返回 (None, [])"""
    if not img_bytes or not getattr(cfg, "DS_API_KEY", ""):
        return None, []

    try:
        import asyncio
        import json
        import requests

        url = DEFAULT_VISION_URL
        model = DEFAULT_VISION_MODEL
        payload = {
            "model": model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/jpeg;base64,{compress_b64(img_bytes)}"}},
                ],
            }],
            "max_tokens": 200,
            "temperature": 0.3,
        }
        headers = {
            "Authorization": f"Bearer {cfg.DS_API_KEY}",
            "Content-Type": "application/json",
        }

        def _post():
            s = requests.Session()
            try:
                return s.post(url, headers=headers, data=json.dumps(payload), timeout=20)
            finally:
                s.close()

        resp = await asyncio.to_thread(_post)
        if resp.status_code != 200:
            log_api(f"[视觉] 失败 {resp.status_code}: {resp.text[:120]}")
            return None, []

        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        desc, tags = parse_reply(text)
        log_api(f"[视觉] {desc[:30]} | 标签 {tags}")
        return desc, tags
    except Exception as e:
        log_api(f"[视觉] 异常: {e}")
        return None, []
