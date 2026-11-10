# ===================== 视觉（v11-A8/A6） =====================
# 图片直接交给多模态模型，拿回「一句人话描述 + 几个标签」。
#
# 设计原则：**失败就当没有**。key 没开视觉、模型下线、网络超时——
# 一律返回 (None, [])，上层退回原来的「用聊天关键词当标签」。

import base64
import io
import os

import botv.core.state as cfg
from ..infra.blocking import run_blocking  # v17.0.3：阻塞调用统一入口
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


def _flatten(im):
    """把带透明通道的图铺到白底上

    GIF/PNG 常有透明背景，直接 convert("RGB") 会变成黑块或雪花，
    模型看到的就是「一张花图」——这是动图被说「看不清」的主因之一。
    """
    try:
        from PIL import Image
        if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
            rgba = im.convert("RGBA")
            bg = Image.new("RGB", rgba.size, (255, 255, 255))
            bg.paste(rgba, mask=rgba.split()[-1])
            return bg
    except Exception:
        pass
    return im.convert("RGB")


MAX_FRAMES = 24     # 动图最多抽这么多帧
GRID_COLS = 4       # 网格列数（24 帧 → 4×6）
FRAME_SIDE = 256    # 单帧缩到这么小再拼


def frame_indices(total, want=MAX_FRAMES):
    """均匀抽帧的序号（含首尾），纯函数便于测试"""
    if total <= 0:
        return []
    if total <= want:
        return list(range(total))
    if want <= 1:
        return [0]
    step = (total - 1) / float(want - 1)
    return sorted({int(round(i * step)) for i in range(want)})


def _tile(frames, cols=GRID_COLS):
    """把多帧拼成一张网格图，按从左到右、从上到下排"""
    from PIL import Image
    if not frames:
        return None
    cell = max(max(f.size) for f in frames)
    rows = (len(frames) + cols - 1) // cols
    canvas = Image.new("RGB", (cols * cell, rows * cell), (255, 255, 255))
    for i, frame in enumerate(frames):
        r, c = divmod(i, cols)
        x = c * cell + (cell - frame.size[0]) // 2
        y = r * cell + (cell - frame.size[1]) // 2
        canvas.paste(frame, (x, y))
    return canvas


def prepare(img_bytes, max_side=MAX_SIDE, quality=JPEG_QUALITY):
    """压缩并返回 (base64, 是否动图, 帧数)；PIL 不可用就原样编码"""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(img_bytes))
        animated = bool(getattr(im, "is_animated", False))
        total = int(getattr(im, "n_frames", 1) or 1)

        if animated and total > 1:
            # 动图：抽帧 → 缩到小图 → 拼网格
            frames = []
            for idx in frame_indices(total):
                try:
                    im.seek(idx)
                    frame = _flatten(im).copy()
                    frame.thumbnail((FRAME_SIDE, FRAME_SIDE))
                    frames.append(frame)
                except Exception:
                    continue
            canvas = _tile(frames)
            if canvas is not None:
                im = canvas
                total = len(frames)
            else:
                im = _flatten(im)
        else:
            im = _flatten(im)

        w, h = im.size
        if max(w, h) > max_side:
            ratio = max_side / float(max(w, h))
            im = im.resize((int(w * ratio), int(h * ratio)))
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=quality)
        return base64.b64encode(buf.getvalue()).decode(), animated, total
    except Exception:
        return base64.b64encode(img_bytes).decode(), False, 1


def compress_b64(img_bytes, max_side=MAX_SIDE, quality=JPEG_QUALITY):
    """只要 base64（兼容旧调用）"""
    return prepare(img_bytes, max_side, quality)[0]


def prompt_with_hint(animated, frames=1):
    """动图要提前告诉模型，不然她会把「一帧」当成整张图"""
    if animated:
        return (PROMPT + f"\n注意：这是一张动图，被抽成 {frames} 帧拼成网格图，"
                         f"按从左到右、从上到下的顺序。请描述画面里发生了什么变化。")
    return PROMPT


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
        b64, animated, frames = prepare(img_bytes)
        payload = {
            "model": model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_with_hint(animated, frames)},
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
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

        resp = await run_blocking(_post, timeout=40, name="vision")  # v17.0.3：统一线程池（视觉较慢，超时放宽）
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
