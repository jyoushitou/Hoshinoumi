# ===================== 连发合并接入（v17.3 U2） =====================
# 把 Coalescer 接到聊天路径上：同一个人连发几句，只回一次。
#
# 只对**私聊的普通文本**生效：
#   - 命令（! 开头）不合并——要秒回
#   - 群聊不合并——群里节奏本来就乱
#   - 代码模式不合并——请求响应式
#   - 图片/语音不合并——消息里没有可用文本
#
# 开关：NAO_BATCH_CHAT=0 可关闭（出问题能立刻回退）

import os

from ..log import log_api
from .coalesce import Coalescer

ENABLED = os.getenv("NAO_BATCH_CHAT", "1") not in ("0", "false", "False", "")


def batchable(message_type, text):
    """这条消息要不要进合并窗口"""
    if not ENABLED:
        return False
    if message_type != "private":
        return False
    text = (text or "").strip()
    if not text or text.startswith("!"):
        return False
    try:
        from ..core import state as cfg

        if cfg.CODE_MODE:
            return False
    except Exception:
        pass
    return True


_handler = None


def set_handler(fn):
    """由 handler 注入回复函数，避免 batcher → handler 反向 import"""
    global _handler
    _handler = fn


async def _handle_batch(target, items):
    """一批消息到齐：拼成一段，交给注入的回复函数处理一次"""
    d, ws, first_text, img_md5s = items[0]
    texts = [t for _, _, t, _ in items if (t or "").strip()]

    if len(items) > 1:
        # 多句拼一起：保留换行，让她看完整意思
        merged = "\n".join(texts)
        log_api(f"[合并] {target} 连发 {len(items)} 条 → 合并成 1 次回复")
    else:
        merged = first_text

    if _handler is None:
        return
    await _handler(d, ws, merged, img_md5s)


_batcher = None


def get_batcher():
    global _batcher
    if _batcher is None:
        _batcher = Coalescer(_handle_batch)
    return _batcher


def set_batcher(b):
    global _batcher
    _batcher = b

