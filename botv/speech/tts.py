# ===================== 语音合成（v11-A10/U13） =====================
# edge-tts 合成 mp3；没装包或合成失败一律返回 None，上层退回纯文字。

import io
import os

from ..log import log_api

# 可选：NAO_VOICE=zh-CN-YunxiNeural 换音色
DEFAULT_VOICE = os.getenv("NAO_VOICE", "zh-CN-XiaoxiaoNeural")
MAX_CHARS = 120


def available():
    """edge-tts 是否可用（没装就静默降级）"""
    try:
        import edge_tts  # noqa: F401
        return True
    except Exception:
        return False


async def synth(text, voice=None):
    """把文字合成 mp3 字节；失败返回 None"""
    text = (text or "").strip()
    if not text or not available():
        return None
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS]

    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice or DEFAULT_VOICE)
        buf = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk.get("type") == "audio" and chunk.get("data"):
                buf.write(chunk["data"])
        data = buf.getvalue()
        if data:
            log_api(f"[语音] 合成成功 {len(data)} bytes")
        return data or None
    except Exception as e:
        log_api(f"[语音] 合成失败: {e}")
        return None
