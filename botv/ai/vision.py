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

# ===================== 视觉模型配置（v18.1） =====================
# 两段式：视觉模型看图 → 文本交给对话模型（DeepSeek）接话。
# DeepSeek 的 chat 接口**不接受 image_url**，所以默认第一段走豆包。

DOUBAO_VISION_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
# 方舟（Ark）通常要填「接入点 ID」（ep-2024xxxx-abc123），不是模型名；
# 新版也支持直接写模型名。视觉任务只用「看图说话」，lite 足够且便宜快。
DOUBAO_VISION_MODEL = "doubao-seed-2.1-lite-260915"
DEEPSEEK_VISION_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_VISION_MODEL = "deepseek-flash"

DEFAULT_VISION_MODEL = os.getenv("NAO_VISION_MODEL", DOUBAO_VISION_MODEL)
DEFAULT_VISION_URL = os.getenv("NAO_VISION_URL", DOUBAO_VISION_URL)


def _local(name, default=""):
    """从 config.local.json 的 vision.* 读取；环境变量优先"""
    try:
        from ..core import settings
        return settings.get("vision." + name, default) or default
    except Exception:
        return default


def vision_key():
    """视觉用哪个 key：专用 key → 豆包 key → DeepSeek key（兜底）"""
    return (os.getenv("NAO_VISION_KEY")
            or _local("key")
            or getattr(cfg, "DOUBAO_API_KEY", "")
            or getattr(cfg, "DS_API_KEY", ""))


def providers():
    """按顺序尝试的后端；环境变量 > config.local.json > 默认

    返回 [{"name","url","model","key"}]，跳过没有 key 的。
    """
    custom_url = os.getenv("NAO_VISION_URL") or _local("url")
    custom_model = os.getenv("NAO_VISION_MODEL") or _local("model")
    custom_key = os.getenv("NAO_VISION_KEY") or _local("key")
    out = []
    if custom_url:
        out.append({"name": "自定义", "url": custom_url,
                    "model": custom_model or DEFAULT_VISION_MODEL,
                    "key": vision_key()})
    else:
        out.append({"name": "豆包", "url": DOUBAO_VISION_URL,
                    "model": custom_model or DOUBAO_VISION_MODEL,
                    "key": (custom_key
                            or getattr(cfg, "DOUBAO_API_KEY", ""))})
        if getattr(cfg, "DS_API_KEY", ""):
            out.append({"name": "DeepSeek", "url": DEEPSEEK_VISION_URL,
                        "model": os.getenv("NAO_VISION_FALLBACK_MODEL")
                        or _local("fallback_model") or DEEPSEEK_VISION_MODEL,
                        "key": cfg.DS_API_KEY})
    return [p for p in out if p.get("key")]
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
    """看图 → (描述, 标签)；所有后端都失败返回 (None, [])

    v18.1：按 providers() 顺序尝试；每次失败都记 status + 响应前 200 字。
    """
    if not img_bytes:
        return None, []

    try:
        b64, animated, frames = prepare(img_bytes)
    except Exception as e:
        log_api(f"[视觉] 预处理失败: {e}")
        return None, []

    import json
    import requests

    for prov in providers():
        try:
            payload = {
                "model": prov["model"],
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text",
                         "text": prompt_with_hint(animated, frames)},
                        {"type": "image_url",
                         "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    ],
                }],
                "max_tokens": 200,
                "temperature": 0.3,
            }
            headers = {"Authorization": f"Bearer {prov['key']}",
                       "Content-Type": "application/json"}

            def _post(url=prov["url"], h=headers, d=json.dumps(payload)):
                s = requests.Session()
                try:
                    return s.post(url, headers=h, data=d, timeout=20)
                finally:
                    s.close()

            resp = await run_blocking(_post, timeout=40, name="vision")

            if resp.status_code != 200:
                # U3/L20：必须能看出是哪一步、为什么，以及怎么改
                hint = ""
                low = (resp.text or "").lower()
                if resp.status_code == 404 or "notfound" in low:
                    hint = ("｜模型/接入点不存在或无权访问："
                            "填方舟的 Model ID（形如 doubao-seed-2.1-lite-260915）"
                            "或接入点 ID（ep-xxxx）")
                elif resp.status_code in (401, 403):
                    hint = "｜key 无效：用「API Key」（Bearer），不是 Access Key"
                log_api(f"[视觉] {prov['name']} HTTP {resp.status_code} | "
                        f"{resp.text[:160]}{hint}")
                continue

            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            desc, tags = parse_reply(text)
            if desc or tags:
                log_api(f"[视觉] {prov['name']} 成功：{desc[:30]} | 标签 {tags}")
                return desc, tags
            log_api(f"[视觉] {prov['name']} 返回空内容")
        except Exception as e:
            log_api(f"[视觉] {prov['name']} 异常: {e}")

    log_api("[视觉] 所有后端都失败，退回「看不清」文案")
    return None, []


async def self_test():
    """!vision test 用：画一张测试图跑一遍，返回可读报告"""
    try:
        from PIL import Image, ImageDraw

        im = Image.new("RGB", (240, 160), (245, 245, 245))
        d = ImageDraw.Draw(im)
        d.rectangle([20, 100, 220, 140], fill=(80, 160, 220))
        d.ellipse([90, 30, 150, 90], fill=(250, 200, 60))
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        img = buf.getvalue()
    except Exception as e:
        return f"❌ 生成测试图失败：{e}"

    import time

    t0 = time.time()
    desc, tags = await describe_image(img)
    cost = time.time() - t0
    provs = providers()
    names = "、".join(p["name"] for p in provs) or "（没有可用的 key）"
    model = provs[0]["model"] if provs else "（未配置）"
    if desc:
        return (f"🖼️ 视觉 ✅（{cost:.1f}s）\n"
                f"   后端：{names}\n"
                f"   描述：{desc[:60]}\n"
                f"   标签：{tags}")
    return (f"🖼️ 视觉 ❌（{cost:.1f}s）\n"
            f"   后端：{names}\n"
            f"   模型：{model}\n"
            f"   看日志里的 [视觉] 行：有 HTTP 状态码 + 怎么改")
