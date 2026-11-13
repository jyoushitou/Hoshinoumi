# ===================== 语音识别（v11-A14） =====================
# 把语音条转成文字。没有可用服务时返回 None，上层用「[语音]」占位。
#
# 默认按 OpenAI 兼容的 /v1/audio/transcriptions 去试 DeepSeek；
# 端点、模型都能用环境变量换，换成别家（豆包/讯飞/本地 whisper）也只要改这两个。

import os

import bot.core.state as cfg
from ..infra.blocking import run_blocking  # v17.0.3：阻塞调用统一入口
from ..log import log_api

DEFAULT_ASR_URL = os.getenv("NAO_ASR_URL", "https://api.deepseek.com/v1/audio/transcriptions")
DEFAULT_ASR_MODEL = os.getenv("NAO_ASR_MODEL", "whisper-1")
MAX_BYTES = 10 * 1024 * 1024  # 超过 10 MB 不传


def _filename_for(url):
    """从 URL 里猜个扩展名，ASR 服务通常靠它判断格式"""
    for ext in (".mp3", ".wav", ".m4a", ".ogg", ".amr", ".silk", ".flac", ".webm"):
        if url and ext in url.lower():
            return "voice" + ext
    return "voice.mp3"


async def transcribe(audio_bytes, source_url=""):
    """返回识别出的文字；不可用/失败返回 None"""
    if not audio_bytes or len(audio_bytes) > MAX_BYTES:
        return None
    key = getattr(cfg, "DS_API_KEY", "")
    if not key:
        return None

    try:
        import asyncio
        import requests

        url = DEFAULT_ASR_URL
        model = DEFAULT_ASR_MODEL
        filename = _filename_for(source_url)

        def _post():
            s = requests.Session()
            try:
                return s.post(
                    url,
                    headers={"Authorization": f"Bearer {key}"},
                    files={"file": (filename, audio_bytes, "application/octet-stream")},
                    data={"model": model},
                    timeout=30,
                )
            finally:
                s.close()

        resp = await run_blocking(_post, timeout=60, name="asr")  # v17.0.3：统一线程池
        if resp.status_code != 200:
            log_api(f"[识别] 失败 {resp.status_code}: {resp.text[:120]}")
            return None

        data = resp.json()
        text = (data.get("text") or "").strip()
        if text:
            log_api(f"[识别] {text[:40]}")
        return text or None
    except Exception as e:
        log_api(f"[识别] 异常: {e}")
        return None
