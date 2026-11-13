# ===================== 兼容层 =====================
# v5-R2：模型调用与回复编排已迁至 bot/ai/client.py
# 本文件只做转发，保证旧 import 路径仍然可用；所有调用方迁完后可删除

from .ai.client import call_deepseek, call_doubao, get_character_reply  # noqa: F401
