# ===================== 兼容层 =====================
# v5-R5：消息主循环已迁至 bot/chat/handler.py，入站解析在 bot/chat/inbound.py
# 本文件只做转发

from .chat.handler import websocket_handle_qq  # noqa: F401
from .chat.inbound import parse_message_content, contains_sticker_key  # noqa: F401
