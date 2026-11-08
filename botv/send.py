# ===================== 兼容层 =====================
# v5-R4：发送实现已迁至 botv/chat/send.py
# 本文件只做转发，保证旧 import 路径仍然可用

from .chat.send import (  # noqa: F401
    select_best_sticker,
    send_private_msg,
    send_group_msg,
    send_short_reply,
    send_sticker_private,
    send_sticker_group,
)
from .chat.reply import build_reply_message  # noqa: F401  旧路径兼容
